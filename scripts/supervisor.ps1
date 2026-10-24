# supervisor: ensure 8788 / 4097 / 8792 / 8790 are listening; start missing ones
$Root = Split-Path -Parent $PSScriptRoot
$GW = Join-Path $Root 'gw\workbuddy2api'
$Py = Join-Path $GW '.venv\Scripts\python.exe'
$LogDir = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir 'supervisor.log'

function Test-Port([int]$p) {
  return [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)
}

"$(Get-Date -Format s) check" | Add-Content -Path $Log

if (-not (Test-Port 8788) -and (Test-Path $Py)) {
  Start-Process -FilePath $Py -WorkingDirectory (Join-Path $GW 'server') -WindowStyle Hidden -ArgumentList @(
    'codebuddy_proxy.py', '--port', '8788', '--endpoint', 'https://www.workbuddy.ai',
    '--platform', 'workbuddy-ai', '--session-file', (Join-Path $env:USERPROFILE '.workbuddy-ai-session.json'),
    '--log-file', (Join-Path $GW 'logs\proxy-intl.jsonl'))
  "  start 8788" | Add-Content -Path $Log
}

if (-not (Test-Port 4097)) {
  Start-Process -FilePath 'powershell' -WindowStyle Hidden -ArgumentList @('-NoProfile', '-Command', 'opencode serve --port 4097 --hostname 127.0.0.1')
  "  start 4097" | Add-Content -Path $Log
  Start-Sleep -Seconds 5
}

if (-not (Test-Port 8792)) {
  Start-Process -FilePath 'node' -WindowStyle Hidden -ArgumentList (Join-Path $Root 'src\opencode-bridge.mjs')
  "  start 8792" | Add-Content -Path $Log
}

if (-not (Test-Port 8790)) {
  $env:IG5_DEBUG = '1'
  Start-Process -FilePath 'node' -WindowStyle Hidden -ArgumentList (Join-Path $Root 'src\ig5-bridge.mjs')
  "  start 8790" | Add-Content -Path $Log
}

Start-Sleep -Seconds 3
"$(Get-Date -Format s) result 8788=$(Test-Port 8788) 4097=$(Test-Port 4097) 8792=$(Test-Port 8792) 8790=$(Test-Port 8790)" | Add-Content -Path $Log
