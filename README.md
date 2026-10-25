# wb-armor 2.1（重构版，无历史包袱）

WorkBuddy / CodeBuddy 本地反代 + 破甲 + 多源路由，供 Codex 与 DeepSeek Harness 使用。
只保留重构后的 **内核 + CLI + 单文件 GUI**；旧面板、旧探针、旧入口已全部删除。

## 一分钟上手

```powershell
cd "C:\Users\Administrator\Desktop\wb 一键破甲反代"
python -m wbarmor start          # 8788 → 4097 → 8792 → 8790
python -m wbarmor deploy-codex   # ~/.codex/config.toml + 绝对路径 catalog
python -m wbarmor deploy-dsh     # 只写 config\dsh-wb.patch.yml，不碰 ~/.dsh/profiles
dsh --profile web --patch .\config\dsh-wb.patch.yml   # 叠加破甲段与 8790 路由
python -m wbarmor open dsh --profile desktop          # desktop 走 Electron 应用本体
python -m wbarmor status
```

图形界面：双击 `启动.cmd`，或 `Start-Process pythonw gui\app.py`。

## 结构

```
wbarmor\core.py     纯函数内核：token、模型目录、部署、服务控制、破甲、载荷、日志
wbarmor\cli.py      python -m wbarmor（6 个高频命令 + adv 收纳其余）
gui\app.py          Tk 控制台（5 个按钮 + 「更多」菜单）
scripts\            start-all / supervisor / bootstrap / launch-app / open-codex / patch-armor / logs / start-wb8788
lib\                log.mjs（Node JSONL）、wlog.ps1（PowerShell JSONL）
src\                ig5-bridge.mjs（8790）、opencode-bridge.mjs（8792）
gw\workbuddy2api\   反代源码（8788）
vendor\             IG5 载荷（flash / full / lazy）
config\             catalog 样本、dsh-wb.patch.yml（deploy-dsh 生成）
attic\              归档：一次性 _patch_/_sync_ 脚本、旧 repair/fix-window/start-proxy
```

## CLI（只记 6 个）

| 命令 | 作用 |
|---|---|
| `status` | 三端口（8788/8790/8792）+ `/health`；可选 4097 单列 |
| `start` / `stop` | 起/停全链路（`stop` 连可选的 4097 一起收） |
| `deploy [all\|codex\|dsh]` | 生成 Codex config 与 `config\dsh-wb.patch.yml` |
| `open codex\|dsh [--profile P]` | 启动客户端；`desktop` 走应用本体 |
| `logs [--tail N] [--comp NAME]` | 合并查看 JSONL 日志 |

其余低频动作（token / inject / models / armor / probe / payload / tasks / token-browser / sync-catalog）统一挂在 `python -m wbarmor adv <cmd>` 下，一级命令面不再增长。

Codex 链路才需要的 4097：`$env:WB_CODEX=1; python -m wbarmor start`。

## 模型选择

`gui/app.py` 右侧列表来自 8790 `/models`（失败回落 8792），双击写 `config.toml` 的 `model`。
CLI 等价：`python -m wbarmor adv models --set deepseek-v4.1-flash-sg`。

## 日志

统一 JSONL：`logs/launcher.log`（启动与 GUI 事件）、`logs/ig5-*.log`、`logs/oc-*.log`、`logs/<port>.err.log`。
查看：`python -m wbarmor logs --comp launcher --tail 20` 或 `scripts\logs.ps1 -Comp launcher`。

## 工程约定

- 路径全部脚本自定位（`__file__` / `$PSScriptRoot`），目录名带空格或中文均可；
- PowerShell 脚本必须存为 **UTF-8 with BOM**，否则 PS 5.1 按 ANSI 解析中文会语法错；
- `.payload` 读取时去 BOM；Python 输出统一按 utf-8 重编码，避免 GBK 控制台崩溃。

## 已知边界

- 端口全局独占，同机不能同时跑两套；
- `deploy-dsh` 覆盖现有 profile（自动 `.bak`）；
- 免费档（8792）无工具协议，仅文本；主链路 429 时自动兜底到免费档。
