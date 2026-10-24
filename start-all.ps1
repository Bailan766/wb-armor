# 一键拉起整条链路：8788 反代 → 4097 opencode serve → 8792 免费外壳 → 8790 IG5 桥

$ErrorActionPreference = 'SilentlyContinue'

$R = 'C:\Users\Administrator\Desktop\wb-armor'

$GW = Join-Path $R 'gw\workbuddy2api'

$PY = Join-Path $GW '.venv\Scripts\python.exe'

$LogDir = Join-Path $R 'logs'

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null



function Up([int]$p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }

# payload selection: .payload file overrides default flash prompt
$payloadFile = Join-Path $R '.payload'
if (Test-Path $payloadFile) {
  $sel = (Get-Content -LiteralPath $payloadFile -Raw -Encoding utf8).Trim()
  if ($sel -and (Test-Path $sel)) { $env:IG5_PAYLOAD = $sel }
}



if (-not (Up 8788) -and (Test-Path $PY)) {

  Start-Process -FilePath $PY -WindowStyle Hidden -WorkingDirectory (Join-Path $GW 'server') -ArgumentList @(

    'codebuddy_proxy.py', '--port', '8788',

    '--endpoint', 'https://www.workbuddy.ai',

    '--platform', 'workbuddy-ai',

    '--session-file', (Join-Path $env:USERPROFILE '.workbuddy-ai-session.json'),

    '--log-file', (Join-Path $GW 'logs\proxy-intl.jsonl')

  )

}

# opencode 在 PATH 里是 npm 的 .cmd shim，Start-Process 不能直接执行 → 用 cmd /c；找不到就退回计划任务

if (-not (Up 4097)) {
  # opencode 是 npm shim：优先 .cmd（cmd /c 可执行），不要拿 .ps1（cmd /c 跑不动）
  $oc = $null
  foreach ($cand in @("$env:APPDATA\npm\opencode.cmd", (Get-Command opencode.cmd -ErrorAction SilentlyContinue).Source)) {
    if ($cand -and (Test-Path $cand)) { $oc = $cand; break }
  }
  if ($oc) {
    Start-Process -FilePath 'cmd.exe' -WindowStyle Hidden -ArgumentList @('/c', $oc, 'serve', '--port', '4097', '--hostname', '127.0.0.1') -ErrorAction SilentlyContinue
  }
  if (-not (Up 4097)) { schtasks /Run /TN OC4097 | Out-Null }   # 兜底
}
Start-Sleep -Seconds 4

# node：优先绝对路径

$node = 'C:\Program Files\nodejs\node.exe'

if (-not (Test-Path $node)) { $node = (Get-Command node -ErrorAction SilentlyContinue).Source }

if ($node -and -not (Up 8792)) { Start-Process -FilePath $node -WindowStyle Hidden -ArgumentList (Join-Path $R 'opencode-bridge.mjs') }

if ($node -and -not (Up 8790)) {

  $env:IG5_DEBUG = '1'

  Start-Process -FilePath $node -WindowStyle Hidden -ArgumentList (Join-Path $R 'ig5-bridge.mjs')

}

Start-Sleep -Seconds 2

foreach ($p in 8788, 4097, 8792, 8790) { "port $p => " + (Up $p) }

