import json, shutil, sys
from pathlib import Path

prof = Path.home() / ".dsh" / "profiles" / "web"
pkg = prof / "package.json"
data = json.loads(pkg.read_text(encoding="utf-8"))
bundles = data.setdefault("dsh", {}).setdefault("profile", {}).setdefault("bundles", [])

# 能解析的：内置 @deepseek-ai/* 或 node_modules 里存在的包；其余剔除
def resolvable(name: str) -> bool:
    if name.startswith("@deepseek-ai/"):
        return True
    p = prof / "node_modules" / name
    if p.exists():
        return True
    scoped = prof / "node_modules" / name.split("/")[0]
    return name.startswith("@") and (prof / "node_modules" / Path(name)).exists()

keep, drop = [], []
for b in bundles:
    (keep if resolvable(b) else drop).append(b)

if drop:
    shutil.copyfile(pkg, str(pkg) + ".bak-bundles")
    data["dsh"]["profile"]["bundles"] = keep
    pkg.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("dropped bundles:", drop)
    print("kept:", keep)
else:
    print("nothing to drop; bundles:", keep)
