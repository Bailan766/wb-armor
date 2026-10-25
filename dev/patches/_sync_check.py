import base64, hashlib, json, os, subprocess, sys, urllib.request

REPO = "Zhengyuuuui/workbuddy2api"
LOCAL = r"C:\Users\Administrator\Desktop\wb 一键破甲反代\gw\workbuddy2api"

def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout

token = sh(["gh", "auth", "token"]).strip()
def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + token,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "wb-armor-sync"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def git_blob_sha(path):
    data = open(path, "rb").read()
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()

head = api(f"/repos/{REPO}/git/ref/heads/main")["object"]["sha"]
tree = api(f"/repos/{REPO}/git/trees/{head}?recursive=1")
up = {n["path"]: n["sha"] for n in tree["tree"] if n["type"] == "blob"}
print("upstream commit:", head[:12], "files:", len(up))

local = {}
for root, _, files in os.walk(LOCAL):
    for f in files:
        p = os.path.join(root, f)
        rel = os.path.relpath(p, LOCAL).replace("\\", "/")
        if rel.startswith(".git/") or "/__pycache__/" in "/" + rel:
            continue
        local[rel] = git_blob_sha(p)

missing = sorted(set(up) - set(local))          # 上游有本地没有
extra = sorted(set(local) - set(up))            # 本地多出来
changed = sorted(k for k in set(up) & set(local) if up[k] != local[k])

print(f"local files: {len(local)}  missing={len(missing)} changed={len(changed)} extra={len(extra)}")
if missing:
    print("-- missing (upstream only) --")
    for m in missing[:20]:
        print("  +", m)
if changed:
    print("-- changed --")
    for c in changed[:30]:
        print("  ~", c)
if extra:
    print("-- extra (local only) --")
    for e in extra[:20]:
        print("  -", e)

json.dump({"head": head, "missing": missing, "changed": changed, "extra": extra},
          open(r"C:\Users\Administrator\Desktop\_sync_plan.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
