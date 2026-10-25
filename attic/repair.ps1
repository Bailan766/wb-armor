param([switch]$NoApp)
$ErrorActionPreference = 'SilentlyContinue'
$Root = Split-Path -Parent $PSScriptRoot
$GW = Join-Path $Root 'gw\workbuddy2api'
$Py = Join-Path $GW '.venv\Scripts\python.exe'
function Up([int]$p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }

# 1) dedupe reverse proxies, keep the one holding the port
$proxies = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*codebuddy_proxy*' })
if ($proxies.Count -gt 1) {
  $keep = ($proxies | Where-Object { (Get-NetTCPConnection -OwningProcess $_.ProcessId -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue) }).ProcessId
  foreach ($p in $proxies) { if ($p.ProcessId -ne $keep) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } }
}

# 2) make sure 8788 is listening
if (-not (Up 8788)) {
  Start-Process -FilePath $Py -WorkingDirectory (Join-Path $GW 'server') -WindowStyle Hidden -ArgumentList @(
    'codebuddy_proxy.py','--port','8788','--endpoint','https://www.workbuddy.ai','--platform','workbuddy-ai',
    '--session-file', (Join-Path $env:USERPROFILE '.workbuddy-ai-session.json'),
    '--log-file', (Join-Path $GW 'logs\proxy-intl.jsonl'))
  Start-Sleep -Seconds 8
}

# 3) restart the Codex app only if it has no visible window
$win = @(Get-Process ChatGPT | Where-Object { $_.MainWindowHandle -ne 0 })
if (-not $NoApp -and $win.Count -eq 0) {
  Get-Process ChatGPT | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
  Start-Process explorer.exe -ArgumentList 'shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App'
  Start-Sleep -Seconds 14
}

$win = @(Get-Process ChatGPT | Where-Object { $_.MainWindowHandle -ne 0 })
$h = $null; try { $h = Invoke-RestMethod 'http://127.0.0.1:8790/health' -TimeoutSec 5 } catch { }
'REPAIR 8788={0} 4097={1} 8792={2} 8790={3} health={4} app_window={5}' -f `
  (Up 8788), (Up 4097), (Up 8792), (Up 8790), $(if ($h) { 'ok' } else { 'DOWN' }), $win.Count
