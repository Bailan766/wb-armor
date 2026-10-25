from pathlib import Path

p = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\wbarmor\core.py")
t = p.read_text(encoding="utf-8")

anchor = 'def open_login_browser(wait: float = 20.0) -> list[str]:'
assert anchor in t

new_fn = '''def login_url() -> str:
    """真正的登录页：/login?platform=<platform>&state=<随机>；WB_LOGIN_URL 可覆盖。"""
    if LOGIN_URL:
        return LOGIN_URL
    state = uuid.uuid4().hex[:16]
    return "https://www.workbuddy.ai/login?platform=%s&state=%s" % (LOGIN_PLATFORM, state)


def _cdp_new_tab(url: str) -> bool:
    """在已开着的调试实例里新开标签页；Chrome 111+ 要求 PUT，旧版用 GET。"""
    import urllib.parse
    target = "http://127.0.0.1:%d/json/new?%s" % (CDP_PORT, urllib.parse.quote(url, safe=""))
    for method in ("PUT", "GET"):
        try:
            req = urllib.request.Request(target, method=method)
            with urllib.request.urlopen(req, timeout=5) as r:
                if r.status in (200, 201):
                    return True
        except Exception:
            continue
    return False


def open_login_browser(wait: float = 20.0) -> list[str]:
    """打开登录页：CDP 已在跑就复用（新标签），否则用独立 profile 起一个带调试端口的窗口。"""
    url = login_url()
    if cdp_ready(CDP_PORT):
        ok = _cdp_new_tab(url)
        return [("reused browser, new tab -> %s" % url) if ok else ("browser up but /json/new failed; open manually: %s" % url),
                "登录完成后点「抓取并注入」"]
    exe = find_browser()
    if not exe:
        return ["没有找到 Chrome/Edge：请先安装 Chrome 或 Edge"]
    BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)
    args = [
        exe,
        "--remote-debugging-port=%d" % CDP_PORT,
        "--user-data-dir=%s" % str(BROWSER_PROFILE),
        "--no-first-run", "--no-default-browser-check",
        "--new-window", url,
    ]
    subprocess.Popen(args, close_fds=True)
    deadline = time.time() + wait
    while time.time() < deadline:
        if cdp_ready(CDP_PORT):
            return ["browser opened (%s) cdp=127.0.0.1:%d" % (os.path.basename(exe), CDP_PORT),
                    "登录页: %s" % url,
                    "登录完成后点「抓取并注入」"]
        time.sleep(0.5)
    return ["browser launched but CDP not ready on %d (另一个实例占用了该端口？)" % CDP_PORT]

'''

start = t.index(anchor)
end = t.index("def capture_tokens(")
t = t[:start] + new_fn + t[end:]

if "import uuid" not in t.split("ROOT =")[0]:
    t = t.replace("import time", "import time\nimport uuid", 1)

p.write_text(t, encoding="utf-8")
print("patched; bytes=", p.stat().st_size)
