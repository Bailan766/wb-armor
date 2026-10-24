param([switch]$NoStart)
# wb-armor 2.0 launcher: optional start-all -> single-instance GUI (gui\app.py)
$ErrorActionPreference = 'SilentlyContinue'
$R = Split-Path -Parent $PSScriptRoot
. (Join-Path $R 'lib\wlog.ps1')

$py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
$pyw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $py -and $pyw) { $py = $pyw }
if (-not $py) {
  Write-Log -Comp launcher -Level error -Msg 'python.missing'
  Write-Host 'python not found in PATH'
  exit 2
}
if (-not $pyw) { $pyw = $py }

$app = Join-Path $R 'gui\app.py'
if (-not (Test-Path $app)) {
  Write-Log -Comp launcher -Level error -Msg 'app.missing' -Extra @{ path = $app }
  Write-Host ('missing app: ' + $app)
  exit 1
}

$running = @(Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' or Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*gui\app.py*' -or $_.CommandLine -like '*gui/app.py*' })
if ($running.Count -gt 0) {
  Write-Log -Comp launcher -Msg 'app.already_running' -Extra @{ pids = (($running | ForEach-Object { $_.ProcessId }) -join ',') }
  Write-Host 'wb-armor GUI already running.'
  exit 0
}

if (-not $NoStart) {
  Write-Log -Comp launcher -Msg 'app.bootstrap_services'
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $R 'scripts\start-all.ps1') | Out-Null
}

$proc = Start-Process -FilePath $pyw -ArgumentList ('"' + $app + '"') -WorkingDirectory $R -PassThru
Start-Sleep -Milliseconds 900
$alive = @(Get-Process -Id $proc.Id -ErrorAction SilentlyContinue).Count -gt 0
Write-Log -Comp launcher -Level (if_ok $alive) -Msg 'app.launched' -Extra @{ pid = $proc.Id; alive = [int]$alive; exe = (Split-Path $pyw -Leaf) }
Write-Host ('wb-armor GUI launched (pid ' + $proc.Id + ')')
