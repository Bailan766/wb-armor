from pathlib import Path

p = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\wbarmor\core.py")
t = p.read_text(encoding="utf-8")

anchor = "def deploy_dsh(headless: bool = False, dry: bool = False) -> list[str]:"
assert anchor in t

helper = '''def _prune_dsh_bundles(profile_dir: Path) -> str:
    """删掉 package.json 里无法解析的 bundle（例如 dsh-purge 未安装），
    否则 DSH 启动时会一直 warning，看起来像"部署没生效"。"""
    pkg = profile_dir / "package.json"
    if not pkg.exists():
        return ""
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return "package.json unreadable: %s" % e
    bundles = data.get("dsh", {}).get("profile", {}).get("bundles") or []
    keep, drop = [], []
    for b in bundles:
        ok = b.startswith("@deepseek-ai/") or (profile_dir / "node_modules" / b).exists()
        (keep if ok else drop).append(b)
    if not drop:
        return ""
    pkg.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return "pruned bundles: %s" % ", ".join(drop)


'''

start = t.index(anchor)
t = t[:start] + helper + t[start:]

# deploy_dsh 里: 写完 profile 后顺便清理 bundle
old = '        out.append("%s %s (array schema, canary=%s)" % ("wrote" if not dry else "would write", t, CANARY in body))'
new = ('        out.append("%s %s (array schema, canary=%s)" % ("wrote" if not dry else "would write", t, CANARY in body))\n'
       '        if not dry:\n'
       '            pruned = _prune_dsh_bundles(t.parent)\n'
       '            if pruned:\n'
       '                out.append(pruned)')
assert old in t
t = t.replace(old, new, 1)

p.write_text(t, encoding="utf-8")
print("core patched with bundle pruning")
