
"""wb-armor GUI 控制器 (tkinter)."""
from __future__ import annotations
import os, sys, json, time, threading, subprocess, urllib.request

import sys as _sys
def _detect_base():
    # 1) 环境变量优先
    env = os.environ.get("WBARMOR_ROOT")
    if env and os.path.isdir(env):
        return env.rstrip("\\/")
    # 2) 从本文件向上找含 wbarmor.ps1 或 gw 的目录
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (here, os.path.dirname(here), os.path.dirname(os.path.dirname(here))):
        if os.path.exists(os.path.join(cand, "wbarmor.ps1")) or os.path.isdir(os.path.join(cand, "gw")):
            return cand
    # 3) 回落默认桌面路径
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE = _detect_base()
GW   = os.path.join(BASE, "gw", "workbuddy2api")
PY   = os.path.join(GW, ".venv", "Scripts", "python.exe")
HOME = os.path.expanduser("~")
SESSION = os.path.join(HOME, ".workbuddy-ai-session.json")
PORTS = {"WB8788": 8788, "OC4097": 4097, "OCB8792": 8792, "IG5B8790": 8790}

OPENCODE_CMD = r"C:\Users\Administrator\AppData\Roaming\npm\opencode.cmd"
NODE_EXE     = r"C:\Program Files\nodejs\node.exe"
DEMO_DIR     = os.path.join(GW, "server")
WB_TOKEN_URL = "https://www.workbuddy.ai"

def resolve_cmd(name, fixed=None):
    """Resolve an executable to an absolute path; prefer a known fixed path,
    then scan PATH for .cmd/.exe/.bat (Windows npm shims are .cmd)."""
    if fixed and os.path.exists(fixed):
        return fixed
    for d in os.environ.get("PATH", "").split(os.pathsep):
        for ext in (".cmd", ".exe", ".bat"):
            c = os.path.join(d, name + ext)
            if os.path.exists(c):
                return c
    return None

def _need(name, fixed=None):
    c = resolve_cmd(name, fixed)
    if not c:
        raise FileNotFoundError("找不到可执行文件: %s（检查 PATH 或安装）" % name)
    return c

def http_json(url, timeout=4):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8", "replace"))

def port_up(p):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        return s.connect_ex(("127.0.0.1", p)) == 0
    finally:
        s.close()

def start_proc_hidden(args, cwd=None, env=None):
    flags = 0x08000000
    e = dict(os.environ)
    if env: e.update(env)
    return subprocess.Popen(args, cwd=cwd, env=e, creationflags=flags,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def start_all():
    log = []
    if not port_up(8788) and os.path.exists(PY):
        start_proc_hidden([PY, "codebuddy_proxy.py", "--port", "8788",
                           "--endpoint", "https://www.workbuddy.ai", "--platform", "workbuddy-ai",
                           "--session-file", SESSION,
                           "--log-file", os.path.join(GW, "logs", "proxy-intl.jsonl")],
                          cwd=os.path.join(GW, "server"))
        log.append("spawned 8788 codebuddy_proxy")
    # 4097 opencode serve：.cmd 需由 cmd.exe 解释，PATH 里是 shim 不是 exe
    if not port_up(4097):
        try:
            oc = _need("opencode", OPENCODE_CMD)
            if oc.lower().endswith((".cmd", ".bat")):
                start_proc_hidden(["cmd.exe", "/c", oc, "serve", "--port", "4097", "--hostname", "127.0.0.1"])
            else:
                start_proc_hidden([oc, "serve", "--port", "4097", "--hostname", "127.0.0.1"])
            log.append("spawned 4097 opencode serve <- " + oc)
        except FileNotFoundError as e:
            log.append("4097 FAIL: " + str(e))
    time.sleep(4)
    # 8792 / 8790 Node 桥：优先绝对 node.exe，回退 PATH
    try:
        node = _need("node", NODE_EXE)
    except FileNotFoundError as e:
        node = None
        log.append("node FAIL: " + str(e))
    if node and not port_up(8792):
        start_proc_hidden([node, os.path.join(BASE, "opencode-bridge.mjs")])
        log.append("spawned 8792 opencode-bridge <- " + node)
    if node and not port_up(8790):
        start_proc_hidden([node, os.path.join(BASE, "ig5-bridge.mjs")], env={"IG5_DEBUG": "1"})
        log.append("spawned 8790 ig5-bridge")

    # 起后复核：任一端口仍 DOWN 就明确报，并在 4097 缺失时给出补救命令
    time.sleep(2)
    down = [p for p in PORTS.values() if not port_up(p)]
    if down:
        log.append("WARN 仍 DOWN: " + ",".join(map(str, down)))
        if 4097 in down:
            log.append("  4097 补救: schtasks /Run /TN OC4097   (或手动: opencode serve --port 4097)")
    return "\n".join(log) if log else "all already up"

def stop_all():
    for name in PORTS:
        subprocess.run(["schtasks", "/End", "/TN", name], capture_output=True, text=True, timeout=10)

def run_verify():
    return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                           "-File", os.path.join(BASE, "verify.ps1")],
                          capture_output=True, text=True, timeout=60).stdout

def run_patch(mode):
    return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                           "-File", os.path.join(BASE, "patch-armor.ps1"), "-Mode", mode],
                          capture_output=True, text=True, timeout=120).stdout

def _load_wb_client():
    """动态载入 workbuddy_ai_client_demo.WorkBuddyAIClient（同一进程内复用其登录/刷新/配置）。"""
    import importlib.util as _iu
    demo = os.path.join(DEMO_DIR, "workbuddy_ai_client_demo.py")
    if not os.path.exists(demo):
        raise FileNotFoundError("找不到 demo: " + demo)
    if DEMO_DIR not in sys.path:
        sys.path.insert(0, DEMO_DIR)
    spec = _iu.spec_from_file_location("wb_demo_runtime", demo)
    mod = _iu.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.WorkBuddyAIClient(WB_TOKEN_URL, session_file=__import__("pathlib").Path(SESSION)), mod

def token_status():
    """按 JWT exp 算 accessToken 剩余时长（只解码 payload，不验签）。"""
    import base64
    if not os.path.exists(SESSION):
        return "无 session"
    try: d = json.load(open(SESSION, encoding="utf-8"))
    except Exception as e: return "session 读取失败: %s" % e
    a = d.get("auth", {}) if isinstance(d.get("auth"), dict) else {}
    at = a.get("accessToken", "") or ""
    if not at:
        return "无 accessToken（需浏览器登录）"
    try:
        payload = at.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        exp = int(claims.get("exp", 0))
        now = int(time.time())
        left = exp - now
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(exp)) if exp else "?"
        if left <= 0:
            return "accessToken 已过期（exp %s），需刷新/重登" % when
        days = left / 86400.0
        return "accessToken 有效，剩余 %.1f 天（exp %s）" % (days, when)
    except Exception as e:
        return "accessToken 存在但解析失败: %s" % e

def wb_browser_login(open_browser=True, timeout=300):
    """浏览器 OAuth 登录：拿 authUrl → 用户浏览器登录 → 轮询 auth/token → 写 session。"""
    client, _ = _load_wb_client()
    client.login(open_browser=open_browser, timeout=timeout)
    return "登录成功: " + str((client.session.get("account") or {}).get("nickname", "-"))

def _setup_codex():
    """幂等把 ~/.codex/config.toml 指到 8790 并选 deepseek-v4.1-flash；缺目录/文件则建。"""
    import re
    cfg = os.path.join(HOME, ".codex", "config.toml")
    cat = os.path.join(HOME, ".codex", "ig5-model-catalog.json")
    os.makedirs(os.path.dirname(cfg), exist_ok=True)
    text = ""
    if os.path.exists(cfg):
        text = open(cfg, encoding="utf-8").read()
    out = []
    done = {"model_provider": False, "model": False}
    for line in text.splitlines():
        m = re.match(r"^\s*(model_provider|model)\s*=", line)
        if m and not done[m.group(1)]:
            done[m.group(1)] = True
            out.append('%s = "%s"' % (m.group(1), "ig5" if m.group(1) == "model_provider" else "deepseek-v4.1-flash"))
        else:
            out.append(line)
    for k in ("model_provider", "model"):
        if not done[k]:
            out.append('%s = "%s"' % (k, "ig5" if k == "model_provider" else "deepseek-v4.1-flash"))
    text = "\n".join(out)
    if "[model_providers.ig5]" not in text:
        text = text.rstrip() + '\n\n[model_providers.ig5]\nbase_url = "http://127.0.0.1:8790/v1"\n'
    open(cfg, "w", encoding="utf-8").write(text)
    # catalog
    if not os.path.exists(cat):
        sample = os.path.join(BASE, "ig5-model-catalog.sample.json")
        if os.path.exists(sample):
            import shutil; shutil.copyfile(sample, cat)
    return "config.toml -> ig5 http://127.0.0.1:8790/v1  model=deepseek-v4.1-flash\n重启 Codex 客户端生效"

def wb_refresh():
    client, _ = _load_wb_client()
    ok = client.refresh()
    return "refresh ok" if ok else "refresh 失败（无 refreshToken 或已过期）"

def inject_token(token, user_id="", kind="device"):
    """Merge credential into session file (0600). kind: device|access|refresh."""
    token = (token or "").strip()
    if not token:
        return False, "token 为空"
    sess = {}
    if os.path.exists(SESSION):
        try: sess = json.load(open(SESSION, encoding="utf-8"))
        except Exception: sess = {}
    sess.setdefault("auth", {}); sess.setdefault("account", {})
    if kind == "device":
        if not token.startswith("v3:") or len(token) < 100:
            return False, "x-device-token 需以 v3: 开头且长度>100（当前 %d 字符）" % len(token)
        sess["_device_token"] = token; sess["_x_device_token"] = token; label = "device_token"
    elif kind == "access":
        sess["auth"]["accessToken"] = token; label = "auth.accessToken"
    elif kind == "refresh":
        sess["auth"]["refreshToken"] = token; label = "auth.refreshToken"
    else:
        return False, "未知类型 %s" % kind
    if user_id:
        sess["account"]["uid"] = user_id
        sess["account"]["oneidAccountId"] = sess["account"].get("oneidAccountId") or user_id
    sess["_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    tmp = SESSION + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(sess, f, indent=2, ensure_ascii=False)
    os.replace(tmp, SESSION)
    return True, "已写入 %s -> %s（%d 字符，前缀 %s）" % (SESSION, label, len(token), token[:8])

def session_summary():
    if not os.path.exists(SESSION):
        return "session 不存在: %s" % SESSION
    try: d = json.load(open(SESSION, encoding="utf-8"))
    except Exception as e: return "读失败: %s" % e
    a = d.get("auth", {}) if isinstance(d.get("auth"), dict) else {}
    acc = d.get("account", {}) if isinstance(d.get("account"), dict) else {}
    at = a.get("accessToken", "") or ""
    dt = d.get("_device_token") or d.get("device_token") or d.get("x_device_token") or ""
    return "\n".join([
        "session: %s" % SESSION,
        "  keys=%s" % list(d.keys()),
        "  accessToken_len=%d prefix=%s" % (len(at), at[:8]),
        "  device_token_len=%d prefix=%s" % (len(dt), dt[:8]),
        "  uid=%s nickname=%s" % (acc.get("uid", "-"), acc.get("nickname", "-")),
    ])

# --------------------------- 图形界面层 ---------------------------
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

BG, CARD, FG, ACC, OKC, BADC = "#0f1419", "#1b232c", "#e6edf3", "#2563eb", "#22c55e", "#ef4444"

class App:
    def __init__(self, root):
        self.root = root
        root.title("wb-armor 控制器  ·  WorkBuddy 反代 / 破甲 / 多源路由")
        root.geometry("960x720")
        root.configure(bg=BG)
        self._style()
        self._build()
        self.refresh()

    def _style(self):
        s = ttk.Style()
        try: s.theme_use("clam")
        except Exception: pass
        s.configure(".", background=BG, foreground=FG)
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=CARD)
        s.configure("TLabel", background=BG, foreground=FG)
        s.configure("H.TLabel", background=BG, foreground=FG, font=("Segoe UI", 13, "bold"))
        s.configure("TButton", font=("Segoe UI", 10), padding=6)
        s.configure("Acc.TButton", background=ACC, foreground="white")
        s.map("Acc.TButton", background=[("active", "#1d4ed8")])

    def _build(self):
        top = ttk.Frame(self.root); top.pack(fill="x", padx=14, pady=(12, 4))
        ttk.Label(top, text="wb-armor 一键控制台", style="H.TLabel").pack(side="left")

        self.portvars = {}
        pf = ttk.Frame(self.root, style="Card.TFrame"); pf.pack(fill="x", padx=14, pady=6)
        for name, p in PORTS.items():
            cell = ttk.Frame(pf, style="Card.TFrame"); cell.pack(side="left", expand=True, padx=8, pady=10)
            v = tk.StringVar(value="…"); self.portvars[name] = v
            ttk.Label(cell, text="%s  :%d" % (name, p), style="TLabel", background=CARD).pack()
            tk.Label(cell, textvariable=v, bg=CARD, fg="#888", font=("Consolas", 20, "bold")).pack()

        bar = ttk.Frame(self.root); bar.pack(fill="x", padx=14, pady=6)
        ttk.Button(bar, text="▶ 一键启动", style="Acc.TButton", command=self.do_start).pack(side="left", padx=4)
        ttk.Button(bar, text="■ 全部停止", command=self.do_stop).pack(side="left", padx=4)
        ttk.Button(bar, text="⟳ 刷新状态", command=self.refresh).pack(side="left", padx=4)
        ttk.Button(bar, text="✔ 验证破甲", command=self.do_verify).pack(side="left", padx=4)
        ttk.Button(bar, text="⚡ DSH 探活", command=self.do_dsh_test).pack(side="left", padx=4)
        ttk.Button(bar, text="🎁 免费档探活", command=self.do_oc_test).pack(side="left", padx=4)
        ttk.Button(bar, text="🔧 配置 Codex", command=self.do_setup_codex).pack(side="left", padx=4)
        ttk.Button(bar, text="🧩 配置 DSH", command=self.do_setup_dsh).pack(side="left", padx=4)
        ttk.Button(bar, text="⟲ 同步模型", command=self.do_sync_models).pack(side="left", padx=4)

        ar = ttk.Frame(self.root); ar.pack(fill="x", padx=14, pady=4)
        ttk.Label(ar, text="模板破甲：").pack(side="left")
        ttk.Button(ar, text="打补丁 patch", command=lambda: self.do_patch("patch")).pack(side="left", padx=4)
        ttk.Button(ar, text="回滚 restore", command=lambda: self.do_patch("restore")).pack(side="left", padx=4)
        ttk.Button(ar, text="取载荷路径", command=self.show_payload).pack(side="left", padx=18)

        tk.Label(self.root, text="凭据注入（抓包所得）", bg=BG, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(10, 0))
        tf = ttk.Frame(self.root); tf.pack(fill="x", padx=14, pady=4)
        self.token = tk.StringVar(); self.uid = tk.StringVar(); self.kind = tk.StringVar(value="device")
        ttk.Label(tf, text="类型").pack(side="left")
        ttk.Combobox(tf, textvariable=self.kind, width=10, state="readonly",
                     values=("device", "access", "refresh")).pack(side="left", padx=4)
        ttk.Label(tf, text="token").pack(side="left")
        e1 = ttk.Entry(tf, textvariable=self.token, width=40, show="•"); e1.pack(side="left", padx=4)
        ttk.Label(tf, text="uid").pack(side="left", padx=(8, 2))
        ttk.Entry(tf, textvariable=self.uid, width=14).pack(side="left")
        ttk.Button(tf, text="注入", command=self.do_inject).pack(side="left", padx=6)
        ttk.Button(tf, text="读当前 session", command=self.show_session).pack(side="left")
        self.showtok = tk.BooleanVar(value=False)
        ttk.Checkbutton(tf, text="显示", variable=self.showtok,
                        command=lambda: e1.configure(show="" if self.showtok.get() else "•")).pack(side="left", padx=6)

        # 浏览器登录 / 刷新 / token 到期
        lf = ttk.Frame(self.root); lf.pack(fill="x", padx=14, pady=(2, 4))
        ttk.Button(lf, text="🌐 浏览器登录", command=self.do_browser_login).pack(side="left", padx=4)
        ttk.Button(lf, text="↻ 刷新 token", command=self.do_refresh).pack(side="left", padx=4)
        ttk.Button(lf, text="拉云端模型", command=self.do_fetch_models).pack(side="left", padx=4)
        self.tokstat = tk.StringVar(value="token: ?")
        tk.Label(lf, textvariable=self.tokstat, bg=BG, fg="#f59e0b", font=("Consolas", 9)).pack(side="left", padx=10)

        cc = ttk.Frame(self.root); cc.pack(fill="x", padx=14, pady=6)
        cfg = "base_url = http://127.0.0.1:8790/v1    api_key = sk-local     model = deepseek-v4.1-flash (或 oc-* 免费档)"
        tk.Label(cc, text=cfg, bg=CARD, fg=OKC, font=("Consolas", 9), anchor="w",
                 padx=8, pady=6).pack(fill="x")

        tk.Label(self.root, text="输出", bg=BG, fg=FG, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14)
        self.out = scrolledtext.ScrolledText(self.root, height=14, bg="#0b0f14", fg="#c9d1d9",
                                             insertbackground="white", font=("Consolas", 9), relief="flat")
        self.out.pack(fill="both", expand=True, padx=14, pady=(2, 12))

    def log(self, *parts):
        msg = " ".join(str(x) for x in parts)
        self.out.insert("end", msg + "\n")   # msg 为整体字符串，逐行插入而非逐字符
        self.out.see("end")

    def bg(self, fn, done=None):
        # worker thread only computes; all Tk calls are marshalled to main via after()
        def run():
            try: r = fn()
            except Exception as e: r = "ERR: %s" % e
            self.root.after(0, lambda: self._bg_done(r, done))
        threading.Thread(target=run, daemon=True).start()

    def _bg_done(self, r, done=None):
        if r: self.log(r)
        if done: done()

    def refresh(self):
        for name, p in PORTS.items():
            up = port_up(p)
            self.portvars[name].set("UP" if up else "DOWN")
            try: self.root.nametowidget(".").nametowidget(self.portvars[name])
            except Exception: pass
        self.log("[refresh]", " ".join("%s=%s" % (n, self.portvars[n].get()) for n in PORTS))
        try:
            st, j = http_json("http://127.0.0.1:8790/health")
            self.log("  /health ok=%s upstream=%s payload=%d chars" % (j.get("ok"), j.get("upstream"), j.get("payload_chars", 0)))
            self.log("  served=%s fallbacks=%s last_model=%s last_status=%s" % (
                j.get("served"), j.get("fallbacks"), j.get("last_model"), j.get("last_status")))
        except Exception as e:
            self.log("  /health 不可达:", e)
        try: self.tokstat.set("token: " + token_status())
        except Exception: pass

    def do_start(self):
        self.log("== 一键启动 =="); self.bg(start_all, self.refresh)

    def do_stop(self):
        self.log("== 停止全部 =="); self.bg(lambda: (stop_all(), "已 end 四个计划任务")[1], self.refresh)

    def do_verify(self):
        self.log("== 验证破甲 =="); self.bg(run_verify, self.refresh)

    def do_sync_models(self):
        self.log("== 同步模型目录（从 8790 拉真实清单）==")
        def work():
            import subprocess
            ps1 = os.path.join(BASE, "wbarmor.ps1")
            if not os.path.exists(ps1):
                return "缺少 wbarmor.ps1"
            r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1, "sync-models"],
                               capture_output=True, text=True, timeout=180)
            return ((r.stdout or "") + (r.stderr or "")).strip()
        self.bg(work, self.refresh)

    def do_patch(self, mode):
        self.log("== 破甲 %s ==" % mode); self.bg(lambda: run_patch(mode), self.refresh)

    def show_payload(self):
        p = os.environ.get("IG5_PAYLOAD") or "C:/Users/Administrator/Desktop/dsh-infinite-gen-5-main/prompts/infinite-gen-5.1-flash.md"
        self.log("载荷:", p, "exists=", os.path.exists(p))

    def do_setup_dsh(self):
        self.log("== 配置 DeepSeek Harness ==")
        def work():
            import subprocess
            ps1 = os.path.join(BASE, "scripts", "setup-dsh.ps1")
            if not os.path.exists(ps1):
                return "缺少 scripts/setup-dsh.ps1"
            r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1],
                               capture_output=True, text=True, timeout=60)
            return (r.stdout or "") + (r.stderr or "")
        self.bg(work)

    def do_setup_codex(self):
        self.log("== 配置 Codex 指向本桥 ==")
        self.bg(lambda: _setup_codex(), None)

    def do_dsh_test(self):
        self.log("== DSH 客户端探活 ==")
        def work():
            lines = []
            # 1) OpenAI 兼容面：/v1/models 拿模型清单
            try:
                st, j = http_json("http://127.0.0.1:8790/v1/models")
                ids = [m.get("id") for m in j.get("data", [])]
                lines.append("/v1/models status=%s count=%d ids=%s" % (st, len(ids), ids[:6]))
            except Exception as e:
                lines.append("/v1/models ERR: %s" % e)
            # 2) 一次最小 chat 调用（走 deepseek-v4.1-flash）
            try:
                import json as _j, urllib.request
                body = _j.dumps({"model": "deepseek-v4.1-flash",
                                 "messages": [{"role": "user", "content": "reply with OK"}],
                                 "stream": False}).encode()
                req = urllib.request.Request("http://127.0.0.1:8790/v1/chat/completions",
                                             data=body, headers={"content-type": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = _j.loads(r.read().decode("utf-8", "replace"))
                txt = ""
                try: txt = data["choices"][0]["message"]["content"][:60]
                except Exception: txt = str(data)[:60]
                lines.append("chat/completions status=%s head=%r" % (r.status, txt))
            except Exception as e:
                lines.append("chat/completions ERR: %s" % e)
            return "\n".join(lines)
        self.bg(work)

    def do_browser_login(self):
        self.log("== 浏览器登录 ==")
        self.log("  " + token_status())
        self.bg(lambda: wb_browser_login(True, 300), self._after_login)

    def _after_login(self, *_):
        self.tokstat.set(token_status())
        self.log("  " + token_status())

    def do_refresh(self):
        self.log("== 刷新 token ==")
        self.bg(wb_refresh, self._after_login)

    def do_fetch_models(self):
        self.log("== 拉云端模型（/v3/config）==")
        def work():
            client, _ = _load_wb_client()
            cfg = client.fetch_cloud_config()
            ms = cfg.get("models") or []
            lines = ["endpoint: %s" % cfg.get("endpoint")]
            for x in ms[:15]:
                if isinstance(x, dict): lines.append("  %-18s | %s" % (x.get("id"), x.get("name", "")))
            return "\n".join(lines)
        self.bg(work)

    def do_oc_test(self):
        self.log("== opencode 免费档探活 (8792) ==")
        def work():
            import json as _j, urllib.request as _u, urllib.error as _e
            lines = []
            # 1) 免费模型清单
            try:
                with _u.urlopen("http://127.0.0.1:8792/v1/models", timeout=6) as r:
                    d = _j.loads(r.read().decode())
                    lines.append("/v1/models ok count=%d ids=%s" % (len(d.get("data", [])), [m["id"] for m in d.get("data", [])][:4]))
            except Exception as ex:
                lines.append("/v1/models ERR: %s" % ex)
            # 2) 一次免费 chat（deepseek-v4.1-flash-free）
            try:
                b = _j.dumps({"model": "deepseek-v4.1-flash-free", "messages": [{"role": "user", "content": "回一个字：好"}]}).encode()
                req = _u.Request("http://127.0.0.1:8792/v1/chat/completions", data=b, headers={"content-type": "application/json"})
                with _u.urlopen(req, timeout=90) as r:
                    d = _j.loads(r.read().decode())
                    msg = d["choices"][0]["message"].get("content", "")
                    lines.append("chat ok head=%r tokens=%s" % (msg[:30], d.get("usage", {}).get("total_tokens")))
            except _e.HTTPError as ex:
                lines.append("chat HTTP %s: %s" % (ex.code, ex.read().decode()[:120]))
            except Exception as ex:
                lines.append("chat ERR: %s" % ex)
            # 3) 经主桥 oc- 路由（走免费档）
            try:
                b = _j.dumps({"model": "oc-deepseek-v4.1-flash-free", "stream": False, "input": "回一个字：行"}).encode()
                req = _u.Request("http://127.0.0.1:8790/v1/responses", data=b, headers={"content-type": "application/json"})
                with _u.urlopen(req, timeout=90) as r:
                    lines.append("bridge oc-route status=%s" % r.status)
            except Exception as ex:
                lines.append("bridge oc-route ERR: %s" % ex)
            return "\n".join(lines)
        self.bg(work)

    def do_inject(self):
        ok, msg = inject_token(self.token.get().strip(), self.uid.get().strip(), self.kind.get())
        self.log(("[OK] " if ok else "[FAIL] ") + msg)
        if ok: self.token.set("")

    def show_session(self):
        for line in session_summary().splitlines():
            self.log(line)

def main():
    root = tk.Tk(); App(root); root.mainloop()

if __name__ == "__main__":
    main()

