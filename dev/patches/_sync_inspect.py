import base64, json, subprocess, urllib.request

REPO = "Zhengyuuuui/workbuddy2api"
token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()

def api(path):
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + token,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "wb-armor-sync"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def content(path):
    d = api(f"/repos/{REPO}/contents/{path}")
    return base64.b64decode(d["content"]).decode("utf-8", "replace")

py = content("pyproject.toml")
print("=== pyproject ===\n" + py[:1200])
proxy = content("server/codebuddy_proxy.py")
print("=== proxy head ===")
print("\n".join(proxy.splitlines()[:40]))
for flag in ("--port", "--endpoint", "--platform", "--session-file", "--log-file", "--device-token"):
    print(f"flag {flag}: {'YES' if flag in proxy else 'NO'}")
print("=== proxy lines:", len(proxy.splitlines()))
