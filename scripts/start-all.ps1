# start-all.ps1 - bring up 8788 (proxy) -> 4097 (opencode serve) -> 8792 (free shim) -> 8790 (IG5 bridge)
# Every attempt writes JSONL into logs\launcher.log and per-service stdout/stderr into logs\<port>.out.log|.err.log

$ErrorActionPreference = 'SilentlyContinue'

$R = Split-Path -Parent $PSScriptRoot
$GW = Join-Path $R 'gw\workbuddy2api'
$PY = Join-Path $GW '.venv\Scripts\python.exe'
$LogDir = Join-Path $R 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

. (Join-Path $R 'lib\wlog.ps1')
Set-Location -LiteralPath $R

function Up([int]$p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }
function PortMap { (@(8788, 4097, 8792, 8790) | ForEach-Object { "" + $_ + "=" + [int](Up $_) }) -join ' ' }
function OutLog([int]$p) { Join-Path $LogDir ("" + $p + ".out.log") }
function ErrLog([int]$p) { Join-Path $LogDir ("" + $p + ".err.log") }

Write-Log -Comp launcher -Msg 'start-all.begin' -Extra @{ ports = (PortMap) }

# payload selection: .payload file overrides the default flash prompt
$payloadFile = Join-Path $R '.payload'
if (Test-Path $payloadFile) {
  $sel = (Get-Content -LiteralPath $payloadFile -Raw -Encoding utf8).Trim()
  if ($sel -and (Test-Path $sel)) { $env:IG5_PAYLOAD = $sel; Write-Log -Comp launcher -Msg 'payload.override' -Extra @{ path = $sel } }
}

# deps bootstrap when the venv is missing
if (-not (Test-Path $PY)) {
  Write-Log -Comp launcher -Level warn -Msg 'bootstrap.start'
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $R 'scripts\bootstrap.ps1') 2>&1 | ForEach-Object { $_ }
  if (-not (Test-Path $PY)) { Write-Log -Comp launcher -Level error -Msg 'bootstrap.venv.missing' -Extra @{ path = $PY } }
}

# 8788 proxy
if (-not (Up 8788) -and (Test-Path $PY)) {
  Start-Process -FilePath $PY -WindowStyle Hidden -WorkingDirectory (Join-Path $GW 'server') `
    -RedirectStandardOutput (OutLog 8788) -RedirectStandardError (ErrLog 8788) `
    -ArgumentList @(
    'codebuddy_proxy.py', '--port', '8788',
    '--endpoint', 'https://www.workbuddy.ai',
    '--platform', 'workbuddy-ai',
    '--session-file', (Join-Path $env:USERPROFILE '.workbuddy-ai-session.json'),
    '--log-file', (Join-Path $GW 'logs\proxy-intl.jsonl')
  )
  Start-Sleep -Milliseconds 1500
  Write-Log -Comp launcher -Level (if_ok (Up 8788)) -Msg 'start.8788' -Extra @{ up = [int](Up 8788) }
}

# 4097 opencode serve (npm shim -> cmd /c)
if (-not (Up 4097)) {
  $oc = $null
  foreach ($cand in @("$env:APPDATA\npm\opencode.cmd", (Get-Command opencode.cmd -ErrorAction SilentlyContinue).Source)) {
    if ($cand -and (Test-Path $cand)) { $oc = $cand; break }
  }
  if ($oc) {
    Start-Process -FilePath 'cmd.exe' -WindowStyle Hidden -RedirectStandardOutput (OutLog 4097) -RedirectStandardError (ErrLog 4097) `
      -ArgumentList @('/c', $oc, 'serve', '--port', '4097', '--hostname', '127.0.0.1')
  } else {
    Write-Log -Comp launcher -Level warn -Msg 'opencode.missing' -Extra @{ hint = 'npm i -g opencode-ai' }
    schtasks /Run /TN OC4097 | Out-Null
  }
}
Start-Sleep -Seconds 4
Write-Log -Comp launcher -Level (if_ok (Up 4097)) -Msg 'start.4097' -Extra @{ up = [int](Up 4097) }

# node absolute path
$node = 'C:\Program Files\nodejs\node.exe'
if (-not (Test-Path $node)) { $node = (Get-Command node -ErrorAction SilentlyContinue).Source }
if (-not $node) { Write-Log -Comp launcher -Level error -Msg 'node.missing' }

if ($node -and -not (Up 8792)) {
  Start-Process -FilePath $node -WindowStyle Hidden -RedirectStandardOutput (OutLog 8792) -RedirectStandardError (ErrLog 8792) `
    -ArgumentList (Join-Path $R 'src\opencode-bridge.mjs')
}

if ($node -and -not (Up 8790)) {
  $env:IG5_DEBUG = '1'
  Start-Process -FilePath $node -WindowStyle Hidden -RedirectStandardOutput (OutLog 8790) -RedirectStandardError (ErrLog 8790) `
    -ArgumentList (Join-Path $R 'src\ig5-bridge.mjs')
}
Start-Sleep -Seconds 3
Write-Log -Comp launcher -Level (if_ok (Up 8792)) -Msg 'start.8792' -Extra @{ up = [int](Up 8792) }
Write-Log -Comp launcher -Level (if_ok (Up 8790)) -Msg 'start.8790' -Extra @{ up = [int](Up 8790) }

# retry pass: a node service can die right after spawn (port busy / bad start); retry once and surface its stderr
foreach ($spec in @(@{ p = 8792; f = 'src\opencode-bridge.mjs' }, @{ p = 8790; f = 'src\ig5-bridge.mjs' })) {
  $pp = [int]$spec.p
  if (-not (Up $pp) -and $node) {
    Write-Log -Comp launcher -Level warn -Msg 'retry' -Extra @{ port = $pp; file = $spec.f }
    Start-Process -FilePath $node -ArgumentList (Join-Path $R $spec.f) -WindowStyle Hidden `
      -RedirectStandardOutput (OutLog $pp) -RedirectStandardError (ErrLog $pp)
    Start-Sleep -Seconds 3
    $ok = Up $pp
    Write-Log -Comp launcher -Level (if_ok $ok) -Msg 'retry.result' -Extra @{ port = $pp; up = [int]$ok }
    if (-not $ok) {
      $tail = ''
      if (Test-Path (ErrLog $pp)) { $tail = ((Get-Content (ErrLog $pp) -Tail 4) -join ' | ') }
      Write-Log -Comp launcher -Level error -Msg 'port.down' -Extra @{ port = $pp; stderr = $tail }
      Write-Host ("WARN port " + $pp + " still down; tail " + (ErrLog $pp))
      if ($tail) { Write-Host $tail }
    }
  }
}

$map = PortMap
Write-Log -Comp launcher -Level (if_ok ($map -notmatch '=0')) -Msg 'start-all.done' -Extra @{ ports = $map }
foreach ($p in 8788, 4097, 8792, 8790) { "port $p => " + (Up $p) }
