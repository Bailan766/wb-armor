# Python launcher (no console window). Prefer pythonw.exe, fall back to python.exe.
$ErrorActionPreference = 'SilentlyContinue'
$R      = 'C:\Users\Administrator\Desktop\wb-armor'
$GUI    = Join-Path $R 'gui\wbarmor_gui.py'
$SELF   = Join-Path $R 'gui\selftest.py'
$pyw    = 'C:\Program Files\Python314\pythonw.exe'
$py     = 'C:\Program Files\Python314\python.exe'
if (-not (Test-Path $pyw)) { $pyw = $py }

# 1) ensure services (idempotent)
$allUp = $true
foreach ($p in 8788,4097,8792,8790) {
  if (-not [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)) { $allUp = $false }
}
if (-not $allUp) { & (Join-Path $R 'start-all.ps1') | Out-Null }

# 2) selftest gate
& $py $SELF | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host 'selftest failed'; exit 1 }

# 2b) single instance guard: if a wbarmor GUI is already up, exit without spawning another
$already = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Where-Object { $_.CommandLine -like '*wbarmor_gui.py*' }
if ($already) { Write-Host "GUI already running."; exit 0 }

# 3) launch GUI with pythonw (hidden console), no window style pop
Start-Process -FilePath $pyw -ArgumentList $GUI -WorkingDirectory $R
Write-Host 'GUI launched.'
