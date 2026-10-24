param([switch]$Force)
# bootstrap: prepare runtime deps on a fresh machine (venv for the reverse proxy, node/opencode check)
$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
$GW = Join-Path $Root 'gw\workbuddy2api'
$Venv = Join-Path $GW '.venv'
$PyExe = Join-Path $Venv 'Scripts\python.exe'

function Find-Python {
  foreach ($c in @('python', 'python3', 'py')) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
  }
  return $null
}

$sysPy = Find-Python
if (-not $sysPy) { 'BOOTSTRAP fail: python not found in PATH (install Python 3.10+)'; exit 2 }

if ($Force -or -not (Test-Path $PyExe)) {
  'BOOTSTRAP creating venv ...'
  & $sysPy -m venv $Venv 2>&1 | Select-Object -Last 3
  if (-not (Test-Path $PyExe)) { "BOOTSTRAP fail: venv not created at $Venv"; exit 3 }
  'BOOTSTRAP installing deps (fastapi uvicorn httpx[socks] requests) ...'
  & $PyExe -m pip install -q --disable-pip-version-check -U pip 2>&1 | Select-Object -Last 2
  & $PyExe -m pip install -q --disable-pip-version-check fastapi uvicorn "httpx[socks]" requests 2>&1 | Select-Object -Last 3
}

$pyOk = $false
if (Test-Path $PyExe) {
  & $PyExe -c "import fastapi,uvicorn,httpx,requests;print('deps_ok')" 2>$null | Out-Null
  $pyOk = ($LASTEXITCODE -eq 0)
}

$node = (Get-Command node -ErrorAction SilentlyContinue)
$ocCands = @("$env:APPDATA\npm\opencode.cmd", (Get-Command opencode.cmd -ErrorAction SilentlyContinue).Source, (Get-Command opencode -ErrorAction SilentlyContinue).Source)
$oc = $ocCands | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

'BOOTSTRAP python_venv={0} deps={1} node={2} opencode={3}' -f (Test-Path $PyExe), $pyOk, [bool]$node, [bool]$oc
if (-not $pyOk) { 'BOOTSTRAP note: 8788 will not start until deps install succeeds' }
if (-not $oc) { 'BOOTSTRAP note: opencode CLI missing -> 4097/8792 free-tier disabled' }
