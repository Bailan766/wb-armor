import base64, hashlib, json, os, shutil, subprocess, sys, urllib.request
from pathlib import Path

REPO = "Zhengyuuuui/workbuddy2api"
LOCAL = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\gw\workbuddy2api")
BACKUP = Path(r"C:\Users\Administrator\Desktop\_archive")
BACKUP.mkdir(parents=True, exist_ok=True)

tok = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "wb-armor-sync"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def git_blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()

head = api(f"/repos/{REPO}/git/ref/heads/main")["object"]["sha"]
tree = api(f"/repos/{REPO}/git/trees/{head}?recursive=1")
blobs = [(n["path"], n["sha"]) for n in tree["tree"] if n["type"] == "blob"]
print("upstream", head[:10], "blobs", len(blobs))

# 1) 备份（跳过 .venv）
if not (BACKUP / f"workbuddy2api-{head[:10]}.zip").exists():
    tmp = BACKUP / "wb2api-tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(LOCAL, tmp, ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc"))
    shutil.make_archive(str(BACKUP / f"workbuddy2api-pre-sync"), "zip", tmp)
    shutil.rmtree(tmp)
    print("backup ->", BACKUP / "workbuddy2api-pre-sync.zip")

# 2) 逐文件写入
written, same = 0, 0
for path, sha in blobs:
    data = base64.b64decode(api(f"/repos/{REPO}/contents/{path}")["content"])
    dest = LOCAL / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and git_blob_sha(dest.read_bytes()) == sha:
        same += 1
        continue
    dest.write_bytes(data)
    written += 1

print("written", written, "already-same", same)

# 3) 复核
bad = []
for path, sha in blobs:
    p = LOCAL / path
    if not p.exists() or git_blob_sha(p.read_bytes()) != sha:
        bad.append(path)
print("verify: files", len(blobs), "mismatch", len(bad), bad[:5])
json.dump({"head": head, "files": len(blobs), "written": written, "mismatch": bad},
          open(r"C:\Users\Administrator\Desktop\_sync_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
