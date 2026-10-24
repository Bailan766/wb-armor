"""wbarmor CLI：无 GUI 也能跑完整流程。"""
from __future__ import annotations

import argparse
import json
import sys
import time

from . import core


def cmd_status(_a) -> int:
    print(json.dumps(core.status(), ensure_ascii=False, indent=2))
    return 0


def cmd_start(_a) -> int:
    ok, out = core.start_all()
    print(out.strip())
    print("START ok=%s" % ok)
    return 0 if ok else 1


def cmd_stop(_a) -> int:
    _, out = core.stop_all()
    print(out.strip())
    print("STOP done")
    return 0


def cmd_token(a) -> int:
    s = core.session_info()
    d = s.days_left()
    print("session=%s exists=%s keys=%s" % (s.path, s.exists, ",".join(s.raw_keys)))
    print("account=%s uid=%s" % (s.nickname or "(none)", s.uid or "(none)"))
    print("accessToken len=%d masked=%s" % (s.access_len, core.mask(s.access)))
    print("deviceToken len=%d" % s.device_len)
    print("expires_in_days=%s" % ("%.1f" % d if d is not None else "unknown"))
    if a.show and s.access:
        print("accessToken=" + s.access)
    if a.refresh:
        ok, msg = core.refresh_token()
        print(("REFRESH ok " if ok else "REFRESH fail ") + msg)
        return 0 if ok else 1
    return 0


def cmd_inject(a) -> int:
    ok, msg = core.inject_device_token(a.token or "")
    print(("OK " if ok else "FAIL ") + msg)
    return 0 if ok else 1


def cmd_models(a) -> int:
    items = core.models_from_bridge()
    cur = core.default_model()
    if a.set:
        ok, msg = core.set_default_model(a.set)
        print(("OK " if ok else "FAIL ") + msg)
        if not ok:
            return 1
        cur = a.set
    if not items:
        print("no models (bridges down?)")
        return 1
    for it in items:
        print("%s %-34s %s" % ("*" if it["id"] == cur else " ", it["id"], it.get("owned_by") or ""))
    print("total=%d current=%s" % (len(items), cur or "(unset)"))
    return 0


def cmd_deploy_codex(_a) -> int:
    for line in core.deploy_codex():
        print(line)
    return 0


def cmd_deploy_dsh(a) -> int:
    for line in core.deploy_dsh(headless=a.headless):
        print(line)
    return 0


def cmd_armor(a) -> int:
    fn = {"status": core.armor_status, "patch": core.armor_patch,
          "restore": core.armor_restore, "verify": core.armor_verify}[a.action]
    for line in fn():
        print(line)
    return 0


def cmd_sync_catalog(_a) -> int:
    ok, lines = core.sync_catalog()
    for line in lines:
        print(line)
    return 0 if ok else 1


def cmd_probe(_a) -> int:
    for line in core.probe():
        print(line)
    return 0


def cmd_payload(a) -> int:
    if a.set:
        ok, msg = core.set_payload(a.set)
        print(("OK " if ok else "FAIL ") + msg)
        return 0 if ok else 1
    info = core.payload_info()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def cmd_logs(a) -> int:
    for line in core.logs_tail(a.tail, a.comp or ""):
        print(line)
    return 0


def cmd_tasks(a) -> int:
    fn = {"status": core.tasks_status, "install": core.tasks_install, "remove": core.tasks_remove}[a.action]
    for line in fn():
        print(line)
    return 0


def cmd_token_browser(a) -> int:
    if not core.cdp_ready(core.CDP_PORT):
        for line in core.open_login_browser():
            print(line)
        if not a.capture:
            print("登录完成后重跑： python -m wbarmor token-browser --capture" + (" --inject" if a.inject else ""))
            return 0
        for _ in range(30):
            if core.cdp_ready(core.CDP_PORT):
                break
            time.sleep(1)
    res = core.capture_tokens()
    if not res.get("ok"):
        print("CAPTURE fail: %s (href=%s)" % (res.get("reason") or "no token", res.get("href") or "?"))
        return 1
    print("CAPTURE ok origin=%s tokens=%d" % (res.get("origin"), res.get("count", 0)))
    for t in res.get("tokens", []):
        v = t.get("value") or ""
        print("  [%s] %s:%s len=%d head=%s" % (t.get("kind"), t.get("storage"), t.get("key"), len(v), core.mask(v, 8)))
    if a.inject:
        ok, lines = core.save_browser_tokens(res.get("tokens", []))
        print(("INJECT ok " if ok else "INJECT fail ") + "; ".join(lines))
        return 0 if ok else 1
    print("提示：加 --inject 可写入 session（auth.accessToken / deviceToken / refreshToken）")
    return 0


def cmd_open(a) -> int:
    for line in core.open_client(a.who):
        print(line)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wbarmor", description="wb-armor control CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("start").set_defaults(fn=cmd_start)
    sub.add_parser("stop").set_defaults(fn=cmd_stop)

    t = sub.add_parser("token")
    t.add_argument("--show", action="store_true")
    t.add_argument("--refresh", action="store_true")
    t.set_defaults(fn=cmd_token)

    i = sub.add_parser("inject")
    i.add_argument("--token", default="")
    i.set_defaults(fn=cmd_inject)

    m = sub.add_parser("models")
    m.add_argument("--set", default="")
    m.set_defaults(fn=cmd_models)

    sub.add_parser("deploy-codex").set_defaults(fn=cmd_deploy_codex)
    d = sub.add_parser("deploy-dsh")
    d.add_argument("--headless", action="store_true")
    d.set_defaults(fn=cmd_deploy_dsh)

    ar = sub.add_parser("armor")
    ar.add_argument("action", choices=["status", "patch", "restore", "verify"], nargs="?", default="status")
    ar.set_defaults(fn=cmd_armor)

    sub.add_parser("sync-catalog").set_defaults(fn=cmd_sync_catalog)
    sub.add_parser("probe").set_defaults(fn=cmd_probe)

    pl = sub.add_parser("payload")
    pl.add_argument("--set", default="")
    pl.set_defaults(fn=cmd_payload)

    lg = sub.add_parser("logs")
    lg.add_argument("--tail", type=int, default=40)
    lg.add_argument("--comp", default="")
    lg.set_defaults(fn=cmd_logs)

    tk = sub.add_parser("tasks")
    tk.add_argument("action", choices=["status", "install", "remove"], nargs="?", default="status")
    tk.set_defaults(fn=cmd_tasks)

    tb = sub.add_parser("token-browser")
    tb.add_argument("--capture", action="store_true")
    tb.add_argument("--inject", action="store_true")
    tb.set_defaults(fn=cmd_token_browser)

    o = sub.add_parser("open")
    o.add_argument("who", choices=["codex", "dsh"])
    o.set_defaults(fn=cmd_open)
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
