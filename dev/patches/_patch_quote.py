import io, re, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代")
INIT = "$ErrorActionPreference = 'SilentlyContinue'"

QFN = """function Q([string]$s) { if ($s -match '\\s') { return '"' + $s + '"' } return $s }
"""

def patch(path: Path, pairs, add_q=True):
    text = path.read_text(encoding="utf-8-sig")
    if add_q and "function Q(" not in text:
        idx = text.find(INIT)
        if idx >= 0:
            end = idx + len(INIT)
            text = text[:end] + "\n" + QFN + text[end:]
        else:
            text = QFN + text
    before = text
    for old, new in pairs:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8-sig")
    print("%-16s changed=%s" % (path.name, before != text))

patch(ROOT / "scripts" / "start-all.ps1", [
    ("-ArgumentList (Join-Path $R 'src\\opencode-bridge.mjs')", "-ArgumentList (Q (Join-Path $R 'src\\opencode-bridge.mjs'))"),
    ("-ArgumentList (Join-Path $R 'src\\ig5-bridge.mjs')", "-ArgumentList (Q (Join-Path $R 'src\\ig5-bridge.mjs'))"),
    ("-ArgumentList (Join-Path $R $spec.f)", "-ArgumentList (Q (Join-Path $R $spec.f))"),
    ("'--session-file', (Join-Path $env:USERPROFILE '.workbuddy-ai-session.json'),",
     "'--session-file', (Q (Join-Path $env:USERPROFILE '.workbuddy-ai-session.json')),"),
    ("'--log-file', (Join-Path $GW 'logs\\proxy-intl.jsonl')",
     "'--log-file', (Q (Join-Path $GW 'logs\\proxy-intl.jsonl'))"),
])

patch(ROOT / "scripts" / "supervisor.ps1", [
    ("-ArgumentList (Join-Path $Root 'src\\opencode-bridge.mjs')", "-ArgumentList (Q (Join-Path $Root 'src\\opencode-bridge.mjs'))"),
    ("-ArgumentList (Join-Path $Root 'src\\ig5-bridge.mjs')", "-ArgumentList (Q (Join-Path $Root 'src\\ig5-bridge.mjs'))"),
    ("-ArgumentList @(\n", "-ArgumentList @(\n"),
])

# 8788 python 参数里的路径也可能含空格：把 supervisor 的 --session-file / --log-file 一并加引号
p = ROOT / "scripts" / "supervisor.ps1"
text = p.read_text(encoding="utf-8-sig")
text = text.replace("'--session-file', (Join-Path $env:USERPROFILE '.workbuddy-ai-session.json')",
                    "'--session-file', (Q (Join-Path $env:USERPROFILE '.workbuddy-ai-session.json'))")
text = text.replace("'--log-file', (Join-Path $GW 'logs\\proxy-intl.jsonl')",
                    "'--log-file', (Q (Join-Path $GW 'logs\\proxy-intl.jsonl'))")
p.write_text(text, encoding="utf-8-sig")
print("supervisor second pass done")
