"""wb-armor 2.1 控制台。

原则：每个按钮 = 一次 core 调用；后台线程执行；状态由定时器刷新；日志去重。
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import time
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wbarmor import core  # noqa: E402


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("wb-armor 2.1")
        self.geometry("1020x720")
        self.minsize(900, 600)
        self.q: queue.Queue = queue.Queue()
        self.models: list[dict] = []
        self._last_log = ""

        self._build()
        self.after(150, self._drain)
        self.after(600, self.refresh_models)
        self.after(900, self.refresh_payload)
        self.after(300, self._tick)

    # ------------------------------------------------------------ layout
    def _build(self) -> None:
        top = ttk.Frame(self, padding=(10, 8))
        top.pack(fill="x")

        # row 1: lifecycle + clients
        r1 = ttk.Frame(top)
        r1.pack(fill="x", pady=2)
        for text, w, cmd in (
            ("▶ 一键启动", 13, self.do_start),
            ("■ 停止全部", 11, self.do_stop),
            ("⟳ 刷新状态", 11, self.refresh_status),
            ("打开 Codex", 11, lambda: self.bg(core.open_client, "codex")),
            ("打开 DSH", 10, lambda: self.bg(core.open_client, "dsh")),
            ("打开日志", 10, self.open_logs),
        ):
            ttk.Button(r1, text=text, width=w, command=cmd).pack(side="left", padx=3)

        # row 2: token + deploy
        r2 = ttk.Frame(top)
        r2.pack(fill="x", pady=2)
        for text, w, cmd in (
            ("① 提 Token", 12, self.do_token),
            ("↻ 刷新 Token", 12, self.do_refresh_token),
            ("② 注入 Token", 12, self.do_inject),
            ("浏览器登录", 11, self.do_browser_login),
            ("抓取并注入", 11, self.do_capture_token),
            ("③ 部署 Codex", 13, lambda: self.bg(core.deploy_codex)),
            ("④ 部署 DSH", 12, lambda: self.bg(core.deploy_dsh)),
            ("同步模型目录", 13, self.do_sync_catalog),
        ):
            ttk.Button(r2, text=text, width=w, command=cmd).pack(side="left", padx=3)

        # row 3: armor + probe
        r3 = ttk.Frame(top)
        r3.pack(fill="x", pady=2)
        for text, w, cmd in (
            ("破甲 Patch", 11, lambda: self.bg(core.armor_patch)),
            ("破甲 恢复", 11, lambda: self.bg(core.armor_restore)),
            ("破甲 校验", 11, lambda: self.bg(core.armor_verify)),
            ("破甲 状态", 11, lambda: self.bg(core.armor_status)),
            ("探活 (8780/8792)", 15, lambda: self.bg(core.probe)),
            ("计划任务", 10, lambda: self.bg(core.tasks_status)),
        ):
            ttk.Button(r3, text=text, width=w, command=cmd).pack(side="left", padx=3)

        # token entry
        tok = ttk.Frame(top)
        tok.pack(fill="x", pady=(6, 2))
        ttk.Label(tok, text="deviceToken").pack(side="left")
        self.token_var = tk.StringVar()
        ttk.Entry(tok, textvariable=self.token_var, show="•").pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(tok, text="清空", width=6, command=lambda: self.token_var.set("")).pack(side="left")

        # payload entry
        pl = ttk.Frame(top)
        pl.pack(fill="x", pady=(2, 2))
        ttk.Label(pl, text="载荷(.md)").pack(side="left")
        self.payload_var = tk.StringVar()
        ttk.Entry(pl, textvariable=self.payload_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(pl, text="浏览", width=6, command=self.pick_payload).pack(side="left", padx=2)
        ttk.Button(pl, text="设为载荷", width=10, command=self.do_set_payload).pack(side="left")
        ttk.Button(pl, text="用内置", width=8, command=self.do_reset_payload).pack(side="left", padx=4)
        self.payload_state = ttk.Label(pl, text="", width=26)
        self.payload_state.pack(side="left", padx=(8, 0))

        # middle: ports + models
        mid = ttk.Frame(self, padding=(10, 4))
        mid.pack(fill="both", expand=False)

        port_box = ttk.LabelFrame(mid, text="端口", padding=6)
        port_box.pack(side="left", fill="y")
        self.port_labels: dict[str, ttk.Label] = {}
        for i, (p, role) in enumerate(core.PORTS.items()):
            ttk.Label(port_box, text="%s %s" % (p, role), width=18).grid(row=i, column=0, sticky="w")
            lb = ttk.Label(port_box, text="?", width=8)
            lb.grid(row=i, column=1, sticky="w")
            self.port_labels[p] = lb

        model_box = ttk.LabelFrame(mid, text="模型（双击设为默认）", padding=6)
        model_box.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.model_list = tk.Listbox(model_box, height=8, activestyle="dotbox")
        self.model_list.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(model_box, command=self.model_list.yview)
        sb.pack(side="left", fill="y")
        self.model_list.configure(yscrollcommand=sb.set)
        self.model_list.bind("<Double-Button-1>", lambda _e: self.set_selected_model())

        side = ttk.Frame(model_box)
        side.pack(side="left", fill="y", padx=(8, 0))
        ttk.Button(side, text="刷新模型", width=11, command=self.refresh_models).pack(pady=2)
        ttk.Button(side, text="设为默认", width=11, command=self.set_selected_model).pack(pady=2)
        self.cur_model = ttk.Label(side, text="默认: ?", wraplength=150)
        self.cur_model.pack(pady=(8, 0))

        # log
        log_box = ttk.LabelFrame(self, text="输出", padding=6)
        log_box.pack(fill="both", expand=True, padx=10, pady=(4, 8))
        self.log = tk.Text(log_box, height=11, wrap="word", state="disabled")
        self.log.pack(side="left", fill="both", expand=True)
        lsb = ttk.Scrollbar(log_box, command=self.log.yview)
        lsb.pack(side="left", fill="y")
        self.log.configure(yscrollcommand=lsb.set)

        self.status = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status, anchor="w", padding=(10, 2)).pack(fill="x")

    # ------------------------------------------------------------ plumbing
    def say(self, text: str) -> None:
        self.q.put(("log", text))

    def _drain(self) -> None:
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    line = str(payload).rstrip()
                    if line and line != self._last_log:
                        self._last_log = line
                        self.log.configure(state="normal")
                        self.log.insert("end", line + "\n")
                        self.log.see("end")
                        self.log.configure(state="disabled")
                elif kind == "status":
                    self.status.set(str(payload))
                elif kind == "models":
                    self._fill_models(payload)
                elif kind == "ports":
                    for p, up in payload.items():
                        lb = self.port_labels.get(p)
                        if lb is not None:
                            lb.configure(text="UP" if up else "DOWN", foreground="#0a7" if up else "#c33")
        except queue.Empty:
            pass
        self.after(150, self._drain)

    def bg(self, fn, *args) -> None:
        def runner() -> None:
            self.q.put(("status", "执行中…"))
            try:
                out = fn(*args)
                for line in (out if isinstance(out, list) else [out]):
                    if line is not None:
                        self.q.put(("log", line))
            except Exception as e:  # noqa: BLE001
                self.q.put(("log", "ERROR: %s" % e))
            finally:
                self.q.put(("status", "就绪"))
        threading.Thread(target=runner, daemon=True).start()

    # ------------------------------------------------------------ status
    def _tick(self) -> None:
        self.refresh_status()
        self.after(5000, self._tick)

    def refresh_status(self) -> None:
        def work():
            try:
                st = core.status()
            except Exception as e:  # noqa: BLE001
                return ["状态读取失败: %s" % e]
            self.q.put(("ports", st["ports"]))
            h = st.get("health") or {}
            self.cur_model.configure(text="默认: %s" % (st.get("model") or "?"))
            return ["ports=%s health=%s served=%s fallbacks=%s model=%s" % (
                "".join("%s:%s " % (p, "1" if u else "0") for p, u in st["ports"].items()),
                h.get("ok"), h.get("served"), h.get("fallbacks"), st.get("model") or "(unset)")]
        self.bg(work)

    def refresh_models(self) -> None:
        def work():
            items = core.models_from_bridge()
            self.models = items
            self.q.put(("models", items))
            if not items:
                return ["模型列表为空：先点「一键启动」，再点「刷新模型」"]
            return ["模型 %d 个，默认 %s" % (len(items), core.default_model() or "(unset)")]
        self.bg(work)

    def _fill_models(self, items) -> None:
        items = items or self.models
        self.model_list.delete(0, "end")
        cur = core.default_model()
        for i, it in enumerate(items):
            self.model_list.insert("end", it["id"] + (("  · " + it["owned_by"]) if it.get("owned_by") else ""))
            if it["id"] == cur:
                self.model_list.selection_clear(0, "end")
                self.model_list.selection_set(i)
                self.model_list.see(i)

    def refresh_payload(self) -> None:
        def work():
            info = core.payload_info()
            self.payload_var.set(info["active"])
            self.payload_state.configure(text="%d bytes" % info["bytes"])
            return ["载荷: %s (%d bytes)" % (info["active"], info["bytes"])]
        self.bg(work)

    # ------------------------------------------------------------ actions
    def do_start(self) -> None:
        def work():
            ok, out = core.start_all()
            return [ln for ln in out.strip().splitlines() if ln.strip()] + ["START %s" % ("OK" if ok else "FAIL")]
        self.bg(work)

    def do_stop(self) -> None:
        def work():
            _, out = core.stop_all()
            return ([ln for ln in out.strip().splitlines() if ln.strip()] or ["stopped"]) + ["STOP done"]
        self.bg(work)

    def do_token(self) -> None:
        def work():
            s = core.session_info()
            d = s.days_left()
            return [
                "session: %s (exists=%s)" % (s.path, s.exists),
                "账号: %s  uid=%s" % (s.nickname or "(none)", s.uid or "(none)"),
                "accessToken: len=%d %s" % (s.access_len, core.mask(s.access)),
                "deviceToken: len=%d" % s.device_len,
                "有效期: %s" % ("%.1f 天" % d if d is not None else "未知"),
                "提示: deviceToken 为空时，把浏览器抓到的 token 粘到输入框再点「注入 Token」",
            ]
        self.bg(work)

    def do_refresh_token(self) -> None:
        def work():
            ok, msg = core.refresh_token()
            return ["refresh %s: %s" % ("OK" if ok else "FAIL", msg)]
        self.bg(work)

    def do_inject(self) -> None:
        tok = self.token_var.get().strip()
        if not tok:
            messagebox.showwarning("注入 Token", "输入框为空：先抓 deviceToken 再粘进来")
            return
        ok, msg = core.inject_device_token(tok)
        self.say(("OK " if ok else "FAIL ") + msg)
        if ok:
            self.token_var.set("")
        self.refresh_status()

    def do_browser_login(self) -> None:
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

    def do_sync_catalog(self) -> None:
        def work():
            ok, lines = core.sync_catalog()
            if ok:
                self.after(200, self.refresh_models)
            return lines
        self.bg(work)

    def pick_payload(self) -> None:
        path = filedialog.askopenfilename(title="选择载荷 markdown", filetypes=[("Markdown", "*.md"), ("All", "*.*")])
        if path:
            self.payload_var.set(path)

    def do_set_payload(self) -> None:
        ok, msg = core.set_payload(self.payload_var.get().strip())
        self.say(("OK " if ok else "FAIL ") + msg)
        if ok:
            self.refresh_payload()

    def do_reset_payload(self) -> None:
        ok, msg = core.reset_payload()
        self.say(("OK " if ok else "FAIL ") + msg)
        if ok:
            self.refresh_payload()

    def open_logs(self) -> None:
        try:
            subprocess.Popen(["explorer.exe", str(core.LOGS)])
            self.say("打开 logs: %s" % core.LOGS)
        except Exception as e:  # noqa: BLE001
            self.say("打开 logs 失败: %s" % e)

    def set_selected_model(self) -> None:
        sel = self.model_list.curselection()
        if not sel:
            messagebox.showinfo("设为默认", "先在模型列表里点一个")
            return
        idx = sel[0]
        model = self.models[idx]["id"] if idx < len(self.models) else self.model_list.get(idx).split("  ")[0]
        ok, msg = core.set_default_model(model)
        self.say(("OK " if ok else "FAIL ") + msg)
        self.cur_model.configure(text="默认: %s" % model)


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
