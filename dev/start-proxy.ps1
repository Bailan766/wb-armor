# WorkBuddy 反代：海外通道 8788，开机自启入口
$d = 'C:\Users\Administrator\Desktop\wb-armor\gw\workbuddy2api'
$py = Join-Path $d '.venv\Scripts\python.exe'
$log = Join-Path $d 'logs\proxy-intl.jsonl'
New-Item -ItemType Directory -Force -Path (Join-Path $d 'logs') | Out-Null
Set-Location (Join-Path $d 'server')
& $py codebuddy_proxy.py --port 8788 `
  --endpoint https://www.workbuddy.ai `
  --platform workbuddy-ai `
  --session-file (Join-Path $env:USERPROFILE '.workbuddy-ai-session.json') `
  --log-file $log *>> (Join-Path $d 'logs\proxy-console.log')
