"""dev/diag_issues.py -- wb-armor 只读体检（2026-10-25 基线）。

用法：python dev/diag_issues.py            # 全查，FAIL 会让退出码 = 失败条数
      python dev/diag_issues.py --only dsh # 只看部署链路

只读：不改任何文件、不发网络请求。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:  # 控制台按 UTF-8 输出，避免 GBK 代码页把中文打成乱码
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
PROFILES = ["web", "desktop", "tauri", "headless"]

rows: list[tuple[str, bool, str]] = []


def check(group: str, name: str, ok: bool, detail: str) -> None:
    rows.append((group, ok, "%s: %s" % (name, detail)))


def read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


# ---------------------------------------------------------------- 1 代码面
core = read("wbarmor/core.py")
head = core.split("def deploy_dsh(")[0]
check("code", "_ensure_dsh_key 有定义", "_ensure_dsh_key" in head,
      "deploy_dsh 第 347 行调用它；缺定义 = 每次部署末尾 NameError")
check("code", "_strip_our_block 认旧标记", "# wb-armor overlay:" in core.split("def _strip_our_block(")[-1][:600],
      "旧版头注释不被剥离 -> 每次重部署多叠一层")
_body = core.split("def deploy_dsh(")[1].split("\ndef ")[0]
check("code", "deploy 不再写 profiles", "DSH_PATCH.write_text" in _body and "prof_dir" not in _body,
      "写 profile 会与 Electron 抢占 desktop，并在换机后留重复条目")
check("code", "_prune_dsh_bundles 真正删条目", 'bundles"] = keep' in core,
      "只算 keep/drop 未回写 -> 永远报 pruned 却从不生效")

adapter = read("gw/workbuddy2api/server/anthropic_adapter.py")
i_txt = adapter.find('messages.append({"role": "user", "content": "\\n".join(text_parts)})')
i_tool = adapter.find("messages.extend(tool_results)")
check("code", "tool 结果先于 user 文本", 0 <= i_tool < i_txt if (i_tool >= 0 and i_txt >= 0) else False,
      "OpenAI 协议要求 tool 消息紧跟 assistant(tool_calls)；夹一条 user 即 11148")

bridge = read("src/ig5-bridge.mjs")
check("code", "/messages 记录上游失败", "messages.upstream" in bridge,
      "现在 catch{} + if(up.ok) 静默落兜底，工具凭空消失且无日志")
check("code", "/health served 聚合三路",
      "served: STATS.routes.responses + STATS.routes.chat + STATS.routes.messages" in bridge,
      "served 只在 /responses 自增 -> 与 served_by_route 对不上")
check("code", "last_status 覆盖全部 POST", "if (post) STATS.lastStatus = code;" in bridge,
      "只有 /responses 会写 last_status，/messages 永远 0")

pkg = read("package.json")
missing = []
if pkg:
    for name, cmd in (json.loads(pkg).get("scripts") or {}).items():
        m = re.search(r"\./([\w./-]+\.(?:ps1|py|mjs))", cmd)
        if m and not (ROOT / m.group(1)).exists():
            missing.append("%s->%s" % (name, m.group(1)))
check("pkg", "npm scripts 指向存在的文件", not missing,
      "失效：" + (", ".join(missing) if missing else "无"))

proxy = read("gw/workbuddy2api/server/codebuddy_proxy.py")
m = re.search(r"MAX_TOOLS\s*=\s*(\d+)", proxy)
check("code", "tools 截断有显式告警", bool(m) and "tools_truncated" in proxy,
      "MAX_TOOLS=%s，超限静默砍尾" % (m.group(1) if m else "?"))

# ---------------------------------------------------------------- 2 部署面
try:
    import yaml  # type: ignore
except Exception:  # noqa: BLE001
    yaml = None

for name in PROFILES:
    f = HOME / ".dsh" / "profiles" / name / "cordis.patch.yml"
    if not f.exists():
        check("dsh", "%s 存在" % name, False, "缺失")
        continue
    text = f.read_text(encoding="utf-8")
    if name == "desktop":   # Electron 独占，本工具不该往里写
        check("dsh", "desktop 未被本工具写入", "# wb-armor overlay" not in text,
              "desktop 由 Electron 管理，写入会重复 agent-default-model/llm-deepseek")
        continue
    ins = len(re.findall(r"(?m)^- insert:", text))
    check("dsh", "%s insert 唯一" % name, ins <= 1, "insert 段 = %d" % ins)
    if yaml is None:
        continue
    try:
        doc = yaml.safe_load(text)
        ids = [x.get("id") for x in doc if isinstance(x, dict)]
        dup = sorted({("<insert>" if k is None else str(k)) for k in ids if ids.count(k) > 1})
        check("dsh", "%s YAML 合法且无重复 id" % name, not dup,
              "entries=%d dup=%s" % (len(doc), ",".join(dup) or "none"))
    except Exception as e:  # noqa: BLE001
        check("dsh", "%s YAML 合法" % name, False, str(e).splitlines()[0])

readme = read("README.md")
check("doc", "README 与 deploy 行为一致", "dsh-wb.patch.yml" in readme,
      "README 应说明用 --patch 叠加，而不是写 profiles")

# ---------------------------------------------------------------- 输出
only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
group_names = {"code": "代码面", "pkg": "工程面", "dsh": "DSH 部署面", "doc": "文档面"}
shown = [r for r in rows if only is None or r[0] == only]
for g in ("code", "pkg", "dsh", "doc"):
    part = [r for r in shown if r[0] == g]
    if not part:
        continue
    print("[%s]" % group_names[g])
    for _g, ok, detail in part:
        print("  %-4s %s" % ("OK" if ok else "FAIL", detail))
bad = [r for r in rows if not r[1]]
print("\n%d 项检查，%d 失败" % (len(rows), len(bad)))
sys.exit(len(bad))
