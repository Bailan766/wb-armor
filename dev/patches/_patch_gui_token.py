from pathlib import Path

p = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\gui\app.py")
t = p.read_text(encoding="utf-8")

old = """            ("② 注入 Token", 12, self.do_inject),"""
new = """            ("② 注入 Token", 12, self.do_inject),
            ("浏览器登录", 11, self.do_browser_login),
            ("抓取并注入", 11, self.do_capture_token),"""
assert old in t, "row2 anchor missing"
t = t.replace(old, new, 1)

anchor = """    def do_sync_catalog(self) -> None:"""
add = '''    def do_browser_login(self) -> None:
        def work():
            return core.open_login_browser()
        self.bg(work)

    def do_capture_token(self) -> None:
        def work():
            lines = []
            if not core.cdp_ready(core.CDP_PORT):
                lines += core.open_login_browser()
                for _ in range(30):
                    if core.cdp_ready(core.CDP_PORT):
                        break
                    time.sleep(1)
            res = core.capture_tokens()
            if not res.get("ok"):
                lines.append("抓取失败: %s (%s)" % (res.get("reason") or "no token", res.get("href") or "?"))
                return lines
            lines.append("抓到 %d 条，origin=%s" % (res.get("count", 0), res.get("origin")))
            for t in res.get("tokens", []):
                v = t.get("value") or ""
                lines.append("  [%s] %s:%s len=%d %s" % (t.get("kind"), t.get("storage"), t.get("key"), len(v), core.mask(v, 8)))
            ok, saved = core.save_browser_tokens(res.get("tokens", []))
            lines.append(("写入 session OK: " if ok else "写入失败: ") + "; ".join(saved))
            if ok:
                self.after(300, self.refresh_status)
            return lines
        self.bg(work)

'''
assert anchor in t, "method anchor missing"
t = t.replace(anchor, add + anchor, 1)

if "import time" not in t.split("import tkinter")[0]:
    t = t.replace("import sys", "import sys\nimport time", 1)

p.write_text(t, encoding="utf-8")
print("gui patched, time import:", "import time" in t)
