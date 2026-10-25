from pathlib import Path

p = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\wbarmor\core.py")
t = p.read_text(encoding="utf-8")

if "_ensure_dsh_key" not in t.split("def deploy_dsh(")[0]:
    anchor = "DSH_PROFILE_NAMES = [\"web\", \"desktop\", \"tauri\"]"
    assert anchor in t
    fn = '''def _ensure_dsh_key() -> str:
    """llm-deepseek 走 provider 路由时必须能取到 DEEPSEEK_API_KEY；桥不校验值。
    已存在则不动（避免覆盖真实 key）。"""
    cur = os.environ.get("DEEPSEEK_API_KEY", "")
    if cur:
        return "DEEPSEEK_API_KEY: already set (%s...), kept" % cur[:6]
    ps = ("[Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY','sk-local-ig5','User');"
          "[Environment]::GetEnvironmentVariable('DEEPSEEK_API_KEY','User')")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    os.environ["DEEPSEEK_API_KEY"] = "sk-local-ig5"
    if r.returncode == 0:
        return "DEEPSEEK_API_KEY: set to sk-local-ig5 (User scope, new process required)"
    return "DEEPSEEK_API_KEY: set for this process only (User scope write failed)"


'''
    t = t.replace(anchor, fn + anchor, 1)
    p.write_text(t, encoding="utf-8")
    print("re-added _ensure_dsh_key")
else:
    print("_ensure_dsh_key present")
