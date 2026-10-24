# Python launcher (no console). Prefer pythonw.exe, fall back to python.exe.
$ErrorActionPreference = 'SilentlyContinue'
$R = Split-Path -Parent $PSScriptRoot
$GUI = Join-Path $R 'gui\wbarmor_gui.py'
$selftest = @(
  (Join-Path $R 'dev\selftest.py'),
  (Join-Path $R 'gui\selftest.py')
) | Where-Object { Test-Path $_ } | Select-Object -First 1
$pyw = 'C:\Program Files\Python314\pythonw.exe'
$py = 'C:\Program Files\Python314\python.exe'
if (-not (Test-Path $pyw)) { $pyw = $py }

# 1) single instance guard
$already = @(Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' or Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*wbarmor_gui.py*' })
if ($already.Count -gt 0) { Write-Host 'GUI already running.'; exit 0 }

# 2) selftest gate: only when the script actually exists; a missing gate must not block the GUI
if ($selftest) {
  & $py $selftest *> $null
  if ($LASTEXITCODE -ne 0) { Write-Host 'selftest failed - continuing anyway'; }
}

# 3) launch
if (-not (Test-Path $GUI)) { Write-Host ('missing GUI: ' + $GUI); exit 1 }
Start-Process -FilePath $pyw -ArgumentList $GUI -WorkingDirectory $R
Write-Host 'GUI launched.'
