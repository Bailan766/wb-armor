import os, sys, json, importlib.util
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("wbarmor_gui", os.path.join(here, "wbarmor_gui.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
fails = 0
def check(name, cond, detail=""):
    global fails
    print(("PASS" if cond else "FAIL"), name, detail)
    if not cond: fails += 1
states = {n: m.port_up(p) for n, p in m.PORTS.items()}
print("ports:", states)
check("four-port probe", set(states.keys()) == set(m.PORTS.keys()))
try:
    st, j = m.http_json("http://127.0.0.1:8790/health")
    check("IG5 /health 200", st == 200 and j.get("ok") is True, "payload=%s" % j.get("payload_chars"))
except Exception as e:
    check("IG5 /health 200", False, str(e))
ok, msg = m.inject_token("short", "", "device")
check("reject bad device token", ok is False, msg)
# real session structure preserved on access-token injection
rs = m.SESSION; bak = None
if os.path.exists(rs): bak = rs + ".selftest.bak"; os.replace(rs, bak)
try:
    before = json.load(open(rs, encoding="utf-8")) if False else {}
    # seed a fake session with auth/account to mimic real shape
    json.dump({"auth": {"accessToken": "OLD", "refreshToken": "R"}, "account": {"uid": "U0"}},
              open(rs, "w", encoding="utf-8"))
    ok1, m1 = m.inject_token("v3:" + "a"*200, "", "device")
    ok2, m2 = m.inject_token("ACCESSTOKEN_NEW", "U1", "access")
    d = json.load(open(rs, encoding="utf-8"))
    good = (ok1 and ok2
            and d["auth"]["accessToken"] == "ACCESSTOKEN_NEW"
            and d["auth"]["refreshToken"] == "R"          # 既有登录态未被破坏
            and d.get("_device_token", "").startswith("v3:")
            and d["account"]["uid"] == "U1")
    check("inject preserves auth subtree + adds device token", good, m1 + " | " + m2)
    summ = m.session_summary()
    check("session summary redacts full token", "ACCESSTOKEN_NEW" not in summ and "accessToken_len=" in summ, summ.splitlines()[2] if len(summ.splitlines())>2 else summ)
finally:
    if os.path.exists(rs): os.remove(rs)
    if bak: os.replace(bak, rs)
print("---- %s ----" % ("ALL PASS" if fails == 0 else "%d FAIL" % fails))
sys.exit(1 if fails else 0)
