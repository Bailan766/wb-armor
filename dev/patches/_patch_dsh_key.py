from pathlib import Path

p = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\wbarmor\core.py")
t = p.read_text(encoding="utf-8")

anchor = 'def deploy_dsh(headless: bool = False, dry: bool = False) -> list[str]:'
assert anchor in t

start = t.index(anchor)
end = t.index("# ---------------------------------------------------------------- services")

new = '''def _ensure_dsh_key() -> str:
    """DSH 的 llm-deepseek 走 provider 路由时必须能取到 DEEPSEEK_API_KEY。
    桥不校验值，任意非空即可；已存在则不动（避免覆盖真实 key）。"""
    cur = os.environ.get("DEEPSEEK_API_KEY", "")
    if cur:
        return "DEEPSEEK_API_KEY: already set (%s...), kept" % cur[:6]
    ps = ("[Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY','sk-local-ig5','User');"
          "[Environment]::GetEnvironmentVariable('DEEPSEEK_API_KEY','User')")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    os.environ["DEEPSEEK_API_KEY"] = "sk-local-ig5"
    if r.returncode == 0:
        return "DEEPSEEK_API_KEY: set to sk-local-ig5 (User scope, needs new process)"
    return "DEEPSEEK_API_KEY: set for this process only (User scope write failed)"


def deploy_dsh(headless: bool = False, dry: bool = False) -> list[str]:
    out: list[str] = []
    targets = [DSH_WEB] + ([DSH_HEADLESS] if headless else [DSH_WEB])
    seen = set()
    for t in targets:
        if t in seen:
            continue
        seen.add(t)
        t.parent.mkdir(parents=True, exist_ok=True)
        if t.exists():
            bak = t.with_suffix(".yml.bak")
            bak.write_text(t.read_text(encoding="utf-8"), encoding="utf-8")
            out.append("backup %s" % bak.name)
        body = _dsh_yaml(armor=True)
        if not dry:
            t.write_text(body, encoding="utf-8")
        out.append("%s %s (array schema, canary=%s)" % ("wrote" if not dry else "would write", t, CANARY in body))
    if not dry:
        out.append(_ensure_dsh_key())
    out.append("verify: dsh --profile headless \\"say OK\\"   (期望首行含 ⟨armor:%s⟩)" % CANARY)
    return out


'''
t = t[:start] + new + t[end:]
p.write_text(t, encoding="utf-8")
print("deploy_dsh rewritten; bytes=", p.stat().st_size)
