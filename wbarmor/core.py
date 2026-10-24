"""wbarmor core: session/token, model catalog, deployments, service control.

单一职责、零全局状态。GUI 与 CLI 都只调这里的函数。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
HOME = Path(os.path.expanduser("~"))
SESSION = HOME / ".workbuddy-ai-session.json"
CODEX_CFG = HOME / ".codex" / "config.toml"
CODEX_CAT = HOME / ".codex" / "ig5-model-catalog.json"
CODEX_SAMPLE = ROOT / "config" / "ig5-model-catalog.sample.json"
DSH_WEB = HOME / ".dsh" / "profiles" / "web" / "cordis.patch.yml"
DSH_HEADLESS = HOME / ".dsh" / "profiles" / "headless" / "cordis.patch.yml"
DSH_SAMPLE_WEB = ROOT / "config" / "dsh-proxy.patch.yml"
BRIDGE = "http://127.0.0.1:8790"
OC_BRIDGE = "http://127.0.0.1:8792"
PORTS = {"8788": "proxy", "4097": "opencode", "8792": "free-shim", "8790": "bridge"}
CANARY = "WB-ARMOR-7F3A"


# ---------------------------------------------------------------- http helpers
def http_json(url: str, timeout: float = 8.0, payload: dict | None = None) -> dict:
    data = None
    headers = {"content-type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def http_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


# ---------------------------------------------------------------- masking
def mask(token: str, keep: int = 6) -> str:
    t = (token or "").strip()
    if not t:
        return "(empty)"
    if len(t) <= keep * 2:
        return t[:2] + "***"
    return t[:keep] + "***" + t[-keep:]


# ---------------------------------------------------------------- session
@dataclass
class SessionInfo:
    exists: bool
    path: Path
    access_len: int
    device_len: int
    refresh_len: int
    uid: str
    nickname: str
    exp_ts: float | None
    raw_keys: list[str]

    @property
    def access(self) -> str:
        return _read_session().get("auth", {}).get("accessToken", "")

    @property
    def device(self) -> str:
        return _read_session().get("auth", {}).get("deviceToken", "") or _read_session().get("device_token", "")

    def days_left(self) -> float | None:
        if not self.exp_ts:
            return None
        return max(0.0, (self.exp_ts - time.time()) / 86400)


def _read_session() -> dict:
    if not SESSION.exists():
        return {}
    try:
        return json.loads(SESSION.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _jwt_exp(token: str) -> float | None:
    try:
        import base64
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        body = json.loads(base64.urlsafe_b64decode(part))
        return float(body.get("exp")) if body.get("exp") else None
    except Exception:
        return None


def session_info() -> SessionInfo:
    d = _read_session()
    auth = d.get("auth", {}) if isinstance(d.get("auth"), dict) else {}
    acc = auth.get("accessToken") or d.get("accessToken") or ""
    dev = auth.get("deviceToken") or d.get("device_token") or ""
    ref = auth.get("refreshToken") or d.get("refreshToken") or ""
    account = d.get("account", {}) if isinstance(d.get("account"), dict) else {}
    return SessionInfo(
        exists=SESSION.exists(),
        path=SESSION,
        access_len=len(acc),
        device_len=len(dev),
        refresh_len=len(ref),
        uid=str(account.get("uid") or auth.get("uid") or ""),
        nickname=str(account.get("nickname") or account.get("email") or ""),
        exp_ts=_jwt_exp(acc),
        raw_keys=sorted(d.keys()),
    )


def inject_device_token(token: str) -> tuple[bool, str]:
    """写入 auth.deviceToken，保留其余字段；空值直接拒绝。"""
    token = (token or "").strip()
    if not token:
        return False, "token 为空"
    if len(token) < 8:
        return False, "token 过短（<8 字符）"
    d = _read_session()
    auth = d.setdefault("auth", {})
    if not isinstance(auth, dict):
        auth = {}
        d["auth"] = auth
    auth["deviceToken"] = token
    SESSION.parent.mkdir(parents=True, exist_ok=True)
    SESSION.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(SESSION, 0o600)
    except Exception:
        pass
    return True, "已写入 deviceToken（%d 字符，掩码 %s）" % (len(token), mask(token))


# ---------------------------------------------------------------- models
def models_from_bridge() -> list[dict]:
    for base in (BRIDGE, OC_BRIDGE):
        for path in ("/models", "/v1/models"):
            try:
                data = http_json(base + path, timeout=6)
                items = data.get("data") or data.get("models") or []
                out = []
                for it in items:
                    mid = it.get("id") or it.get("model")
                    if mid:
                        out.append({"id": mid, "owned_by": it.get("owned_by", ""), "source": base})
                if out:
                    return out
            except Exception:
                continue
    return []


def default_model() -> str:
    text = CODEX_CFG.read_text(encoding="utf-8") if CODEX_CFG.exists() else ""
    m = re.search(r'(?m)^model\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else ""


def set_default_model(model: str) -> tuple[bool, str]:
    model = (model or "").strip()
    if not model:
        return False, "model 为空"
    text = CODEX_CFG.read_text(encoding="utf-8") if CODEX_CFG.exists() else ""
    if re.search(r'(?m)^model\s*=', text):
        text = re.sub(r'(?m)^model\s*=\s*"[^"]*"', 'model = "%s"' % model, text, count=1)
    else:
        text = 'model = "%s"\n' % model + text
    CODEX_CFG.parent.mkdir(parents=True, exist_ok=True)
    CODEX_CFG.write_text(text, encoding="utf-8")
    return True, "config.toml model -> %s" % model


# ---------------------------------------------------------------- deploy: codex
def deploy_codex(dry: bool = False) -> list[str]:
    logs: list[str] = []
    CODEX_CFG.parent.mkdir(parents=True, exist_ok=True)
    text = CODEX_CFG.read_text(encoding="utf-8") if CODEX_CFG.exists() else ""
    if not re.search(r'(?m)^model_provider\s*=', text):
        text = 'model_provider = "ig5"\n' + text
    if not re.search(r'(?m)^model\s*=', text):
        text = text.replace('model_provider = "ig5"\n', 'model_provider = "ig5"\nmodel = "deepseek-v4.1-flash"\n', 1)
    cat_line = 'model_catalog_json = "%s"' % str(CODEX_CAT).replace("\\", "/")
    if re.search(r"(?m)^model_catalog_json\s*=", text):
        text = re.sub(r"(?m)^model_catalog_json\s*=.*$", cat_line, text, count=1)
    else:
        text = text.replace('model = "', cat_line + '\nmodel = "', 1) if '\nmodel = "' in text else text + "\n" + cat_line + "\n"
    if "[model_providers.ig5]" not in text:
        text = text.rstrip() + (
            '\n\n[model_providers.ig5]\nname = "IG5 Bridge (local)"\n'
            'base_url = "http://127.0.0.1:8790/v1"\nwire_api = "responses"\n'
            'requires_openai_auth = false\nexperimental_bearer_token = "sk-local-ig5"\n'
        )
    if not dry:
        CODEX_CFG.write_text(text, encoding="utf-8")
    logs.append("config.toml: provider=ig5 model=%s" % (default_model() or "deepseek-v4.1-flash"))
    logs.append("model_catalog_json=%s (absolute)" % str(CODEX_CAT).replace("\\", "/"))
    if not CODEX_CAT.exists() and CODEX_SAMPLE.exists():
        CODEX_CAT.write_text(CODEX_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        logs.append("catalog: created from sample")
    else:
        logs.append("catalog: exists=%s" % CODEX_CAT.exists())
    return logs


# ---------------------------------------------------------------- deploy: dsh
def _dsh_yaml(armor: bool) -> str:
    payload = ROOT / "vendor" / "dsh-infinite-gen-5" / "infinite-gen-5.1-flash.md"
    if not payload.exists():
        payload = ROOT / "vendor" / "dsh-infinite-gen-5" / "infinite-gen-5.full.md"
    sys_prompt = ("<< armorset >>\n" + payload.read_text(encoding="utf-8")) if armor and payload.exists() else "You are a helpful assistant."
    return (
        "# wb-armor: point DSH at the local bridge\n"
        "plugins:\n"
        "  llm-deepseek:\n"
        "    baseURL: http://127.0.0.1:8790/v1\n"
        "    apiKey: sk-local-ig5\n"
        "    models:\n"
        "      - deepseek-v4.1-flash\n"
        "      - deepseek-v4.1-flash-sg\n"
        "      - deepseek-v4-flash\n"
        "  agent-default-model:\n"
        "    provider: llm-deepseek\n"
        "    model: deepseek-v4.1-flash\n"
        "  system-prompt:\n"
        "    content: |\n"
        + "".join("      " + ln + "\n" for ln in sys_prompt.splitlines()[:400])
        + "\n# canary: %s\n" % CANARY
    )


def deploy_dsh(headless: bool = False, dry: bool = False) -> list[str]:
    out: list[str] = []
    targets = [DSH_WEB] + ([DSH_HEADLESS] if headless else [])
    for t in targets:
        t.parent.mkdir(parents=True, exist_ok=True)
        if t.exists():
            bak = t.with_suffix(".yml.bak")
            bak.write_text(t.read_text(encoding="utf-8"), encoding="utf-8")
            out.append("backup %s" % bak.name)
        if not dry:
            t.write_text(_dsh_yaml(armor=True), encoding="utf-8")
        out.append("wrote %s (canary=%s)" % (t, CANARY in _dsh_yaml(True)))
    return out


# ---------------------------------------------------------------- services
def port_up(port: int) -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=1.2) as r:
            return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def _ps(script: str, *args: str) -> subprocess.CompletedProcess:
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, *args]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300)


def start_all() -> tuple[bool, str]:
    p = _ps(str(ROOT / "scripts" / "start-all.ps1"))
    ok = all(port_up(int(x)) for x in PORTS if x != "8788") and http_ok(BRIDGE + "/health")
    return ok, (p.stdout or "") + (p.stderr or "")


def stop_all() -> tuple[bool, str]:
    p = _ps(str(ROOT / "wbarmor.ps1"), "down")
    return True, (p.stdout or "") + (p.stderr or "")


def status() -> dict:
    st = {p: port_up(int(p)) for p in PORTS}
    health = {}
    try:
        health = http_json(BRIDGE + "/health", timeout=4)
    except Exception:
        health = {}
    return {"ports": st, "health": health, "model": default_model()}


# ---------------------------------------------------------------- launcher
def open_client(which: str) -> list[str]:
    if which == "codex":
        p = _ps(str(ROOT / "scripts" / "open-codex.ps1"))
        return [(p.stdout or "").strip()] if p.returncode == 0 else ["codex launch failed: " + (p.stderr or "").strip()]
    if which == "dsh":
        subprocess.Popen(["cmd", "/c", "start", "", "dsh", "--profile", "web"], cwd=str(ROOT))
        return ["dsh --profile web"]
    return ["unknown client: " + which]
# ---------------------------------------------------------------- armor (patch/restore/verify)
TEMPLATES = Path(r"C:\Program Files\WorkBuddyAI\resources\app.asar.unpacked\resources\templates")


def _ps(script: str, *args: str) -> subprocess.CompletedProcess:
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, *args]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)


def _run_lines(script: Path, *args: str) -> list[str]:
    p = _ps(str(script), *args)
    out = [ln for ln in ((p.stdout or "") + (p.stderr or "")).splitlines() if ln.strip()]
    return out or ["(no output, exit=%d)" % p.returncode]


def armor_patch() -> list[str]:
    return _run_lines(ROOT / "scripts" / "patch-armor.ps1", "-Mode", "patch")


def armor_restore() -> list[str]:
    return _run_lines(ROOT / "scripts" / "patch-armor.ps1", "-Mode", "restore")


def armor_verify() -> list[str]:
    return _run_lines(ROOT / "scripts" / "verify.ps1")


def armor_status() -> list[str]:
    if not TEMPLATES.exists():
        return ["templates 目录不存在: %s" % TEMPLATES]
    files = sorted(TEMPLATES.glob("*.tpl"))
    if not files:
        return ["没有找到 *.tpl: %s" % TEMPLATES]
    rows = []
    armed = 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            rows.append("%-40s unreadable: %s" % (f.name, e))
            continue
        has_canary = CANARY in text
        has_policy = "<content_policy>" in text
        state = "ARMOR-OFF" if (has_canary and not has_policy) else ("ORIGINAL" if has_policy else "NO-POLICY")
        if state == "ARMOR-OFF":
            armed += 1
        rows.append("%-40s %-10s bytes=%d" % (f.name, state, len(text.encode("utf-8"))))
    rows.append("patched=%d / total=%d" % (armed, len(files)))
    return rows


# ---------------------------------------------------------------- payload
def payload_info() -> dict:
    sel = ROOT / ".payload"
    current = ""
    if sel.exists():
        current = sel.read_text(encoding="utf-8", errors="replace").strip().lstrip("\ufeff").strip()
    default = ROOT / "vendor" / "dsh-infinite-gen-5" / "infinite-gen-5.1-flash.md"
    active = current if (current and Path(current).exists()) else (str(default) if default.exists() else "")
    size = Path(active).stat().st_size if active and Path(active).exists() else 0
    return {"selector": str(sel), "selected": current, "active": active, "bytes": size, "default": str(default)}


def set_payload(path: str) -> tuple[bool, str]:
    p = Path(path).expanduser()
    if not p.exists():
        return False, "文件不存在: %s" % p
    (ROOT / ".payload").write_text(str(p), encoding="utf-8")
    return True, "载荷已指向 %s (%d bytes)" % (p, p.stat().st_size)


# ---------------------------------------------------------------- catalog sync
def catalog_template() -> dict:
    """用现有 catalog 的第一条做模板，保证字段形状被 Codex 接受。"""
    raw = {}
    if CODEX_CAT.exists():
        try:
            raw = json.loads(CODEX_CAT.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
    models = raw.get("models") or []
    return (models[0] if models else {}), raw


def sync_catalog() -> tuple[bool, list[str]]:
    items = models_from_bridge()
    if not items:
        return False, ["拉取失败：8790 /models 不可达"]
    tpl, raw = catalog_template()
    if not tpl:
        sample = CODEX_SAMPLE
        if sample.exists():
            try:
                raw = json.loads(sample.read_text(encoding="utf-8"))
                tpl = (raw.get("models") or [{}])[0]
            except Exception:
                tpl = {}
    models = []
    for it in items:
        entry = json.loads(json.dumps(tpl)) if tpl else {}
        entry["slug"] = it["id"]
        entry.setdefault("display_name", it["id"])
        if not entry.get("base_instructions"):
            entry["base_instructions"] = "You are a coding agent. [ARMOR_OFF CANARY=%s]" % CANARY
        models.append(entry)
    out = {"models": models}
    CODEX_CAT.parent.mkdir(parents=True, exist_ok=True)
    CODEX_CAT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return True, ["catalog 写入 %d 个模型 -> %s" % (len(models), CODEX_CAT)]


# ---------------------------------------------------------------- probe
def probe() -> list[str]:
    rows = []
    t0 = time.time()
    try:
        h = http_json(BRIDGE + "/health", timeout=5)
        rows.append("8790 /health ok=%s payload=%s chars served=%s fallbacks=%s (%.0f ms)"
                    % (h.get("ok"), h.get("payload_chars"), h.get("served"), h.get("fallbacks"), (time.time() - t0) * 1000))
    except Exception as e:  # noqa: BLE001
        rows.append("8790 /health FAIL: %s" % e)
    t0 = time.time()
    try:
        r = http_json(BRIDGE + "/v1/responses", timeout=120,
                      payload={"model": default_model() or "deepseek-v4.1-flash", "stream": False,
                               "input": "ping (reply with one word)"})
        txt = ""
        try:
            txt = r["output"][0]["content"][0]["text"]
        except Exception:
            txt = json.dumps(r)[:120]
        rows.append("8790 responses OK %.0f ms: %s" % ((time.time() - t0) * 1000, txt[:80].replace("\n", " ")))
    except Exception as e:  # noqa: BLE001
        rows.append("8790 responses FAIL %.0f ms: %s" % ((time.time() - t0) * 1000, e))
    t0 = time.time()
    try:
        r = http_json(OC_BRIDGE + "/v1/chat/completions", timeout=120,
                      payload={"model": "deepseek-v4.1-flash-free",
                               "messages": [{"role": "user", "content": "ping"}]})
        txt = r["choices"][0]["message"]["content"]
        rows.append("8792 free-tier OK %.0f ms: %s" % ((time.time() - t0) * 1000, txt[:60].replace("\n", " ")))
    except Exception as e:  # noqa: BLE001
        rows.append("8792 free-tier FAIL %.0f ms: %s" % ((time.time() - t0) * 1000, e))
    return rows


# ---------------------------------------------------------------- token refresh (reuse demo client)
def refresh_token() -> tuple[bool, str]:
    demo_dir = ROOT / "gw" / "workbuddy2api" / "server"
    demo = demo_dir / "workbuddy_ai_client_demo.py"
    if not demo.exists():
        return False, "缺少 demo: %s" % demo
    code = (
        "import sys; sys.path.insert(0, %r)\n" % str(demo_dir)
        + "from workbuddy_ai_client_demo import WorkBuddyAIClient\n"
        + "c = WorkBuddyAIClient()\n"
        + "print('refresh_ok' if c.refresh() else 'refresh_fail')\n"
    )
    p = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    out = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
    tail = out[-1] if out else "(no output)"
    return ("refresh_ok" in tail), tail


# ---------------------------------------------------------------- logs
def logs_tail(n: int = 40, comp: str = "") -> list[str]:
    rows: list[tuple[float, str]] = []
    if not LOGS.exists():
        return ["logs 目录不存在: %s" % LOGS]
    for f in LOGS.glob("*.log"):
        if comp and comp not in f.name:
            continue
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
        except Exception:
            continue
        for ln in lines:
            rows.append((f.stat().st_mtime, "%s | %s" % (f.name, ln)))
    rows.sort(key=lambda t: t[0])
    return [r[1] for r in rows[-n:]] or ["(空)"]


# ---------------------------------------------------------------- scheduled tasks
TASKS = {"WB8788": "start-wb8788.ps1", "OC4097": None, "OCB8792": "opencode-bridge.mjs",
         "IG5B8790": "ig5-bridge.mjs", "WBSupervisor": "supervisor.ps1"}


def tasks_status() -> list[str]:
    rows = []
    for name in TASKS:
        p = subprocess.run(["schtasks", "/Query", "/TN", name, "/FO", "LIST"], capture_output=True, text=True)
        state = "MISSING"
        if p.returncode == 0:
            for ln in (p.stdout or "").splitlines():
                if ln.lower().startswith("status:"):
                    state = ln.split(":", 1)[1].strip()
                    break
        rows.append("%-14s %s" % (name, state))
    return rows


def tasks_install() -> list[str]:
    py = _ps(str(ROOT / "scripts" / "start-wb8788.ps1"))  # no-op probe, keeps path warm
    out = []
    specs = [
        ("WB8788", "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File %s" % (ROOT / "scripts" / "start-wb8788.ps1"), "ONLOGON"),
        ("OCB8792", 'node "%s"' % (ROOT / "src" / "opencode-bridge.mjs"), "ONLOGON"),
        ("IG5B8790", 'node "%s"' % (ROOT / "src" / "ig5-bridge.mjs"), "ONLOGON"),
        ("WBSupervisor", "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File %s" % (ROOT / "scripts" / "supervisor.ps1"), "MINUTE"),
    ]
    for name, tr, sched in specs:
        args = ["schtasks", "/Create", "/TN", name, "/TR", tr, "/SC", sched, "/RL", "LIMITED", "/F"]
        if sched == "MINUTE":
            args[args.index("/SC"):args.index("/SC") + 2] = ["/SC", "MINUTE", "/MO", "5"]
        p = subprocess.run(args, capture_output=True, text=True)
        out.append("%-14s %s" % (name, "OK" if p.returncode == 0 else "FAIL: " + (p.stdout + p.stderr).strip()[:80]))
    return out


def tasks_remove() -> list[str]:
    out = []
    for name in TASKS:
        p = subprocess.run(["schtasks", "/Delete", "/TN", name, "/F"], capture_output=True, text=True)
        out.append("%-14s %s" % (name, "deleted" if p.returncode == 0 else "absent"))
    return out
