# Python launcher for the GUI (no console window). Prefer pythonw.exe, fall back to python.exe.
$ErrorActionPreference = 'SilentlyContinue'
$R = Split-Path -Parent $PSScriptRoot
. (Join-Path $R 'lib\wlog.ps1')

$GUI = Join-Path $R 'gui\wbarmor_gui.py'
$selftest = @(
  (Join-Path $R 'dev\selftest.py'),
  (Join-Path $R 'gui\selftest.py')
) | Where-Object { Test-Path $_ } | Select-Object -First 1
$pyw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
$py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $pyw) { $pyw = $py }
if (-not $py) {
  Write-Log -Comp launcher -Level error -Msg 'python.missing'
  Write-Host 'python not found in PATH'
  exit 2
}

# 1) single instance guard
$already = @(Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' or Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*wbarmor_gui.py*' })
if ($already.Count -gt 0) {
  Write-Log -Comp launcher -Msg 'gui.already_running' -Extra @{ pids = (($already | ForEach-Object { $_.ProcessId }) -join ',') }
  Write-Host 'GUI already running.'
  exit 0
}

# 2) selftest gate: missing script never blocks; failure is logged but not fatal
if ($selftest) {
  & $py $selftest *> $null
  $code = $LASTEXITCODE
  Write-Log -Comp launcher -Level (if_ok ($code -eq 0)) -Msg 'selftest' -Extra @{ exit = $code; script = (Split-Path $selftest -Leaf) }
  if ($code -ne 0) { Write-Host 'selftest failed - continuing anyway' }
} else {
  Write-Log -Comp launcher -Level warn -Msg 'selftest.missing'
}

# 3) launch
if (-not (Test-Path $GUI)) {
  Write-Log -Comp launcher -Level error -Msg 'gui.missing' -Extra @{ path = $GUI }
  Write-Host ('missing GUI: ' + $GUI)
  exit 1
}
$proc = Start-Process -FilePath $pyw -ArgumentList $GUI -WorkingDirectory $R -PassThru
Start-Sleep -Milliseconds 800
$alive = @(Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Id -eq $proc.Id }).Count -gt 0
Write-Log -Comp launcher -Level (if_ok $alive) -Msg 'gui.launched' -Extra @{ pid = $proc.Id; alive = [int]$alive; exe = (Split-Path $pyw -Leaf) }
Write-Host 'GUI launched.'
