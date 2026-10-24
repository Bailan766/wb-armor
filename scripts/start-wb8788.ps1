$GW = Join-Path (Split-Path -Parent $PSScriptRoot) 'gw\workbuddy2api'
$PY = Join-Path $GW '.venv\Scripts\python.exe'
Set-Location (Join-Path $GW 'server')
& $PY codebuddy_proxy.py --port 8788 `
  --endpoint https://www.workbuddy.ai `
  --platform workbuddy-ai `
  --session-file (Join-Path $env:USERPROFILE '.workbuddy-ai-session.json') `
  --log-file (Join-Path $GW 'logs\proxy-intl.jsonl')
