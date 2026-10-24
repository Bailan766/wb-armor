$ErrorActionPreference = 'SilentlyContinue'
$Root = 'C:\Users\Administrator\Desktop\wb-armor'
function PortUp([int]$p) { return [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }

# 1) services
if ((-not (PortUp 8790)) -or (-not (PortUp 8788))) {
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'supervisor.ps1') | Out-Null
  Start-Sleep -Seconds 8
}

# 2) catalog: ensure deepseek button entry
$cat = Join-Path $env:USERPROFILE '.codex\ig5-model-catalog.json'
$need = 'deepseek-v4.1-flash'
$has = $false
if (Test-Path $cat) {
  try {
    $raw = Get-Content $cat -Raw
    $has = $raw -match ('"slug"\s*:\s*"' + [regex]::Escape($need) + '"')
    if (-not $has) { Copy-Item $cat ($cat + '.bak') -Force }
  } catch { $has = $false }
}

# 3) probe model list + one completion
$models = 0; $modelOk = $false; $text = ''
try {
  $m = Invoke-RestMethod 'http://127.0.0.1:8790/v1/models' -TimeoutSec 10
  $models = @($m.data).Count
  $modelOk = (@($m.data | Where-Object { $_.id -eq $need })).Count -gt 0
} catch { $text = 'MODELS_ERR' }
if (-not $text) {
  # 走 /v1/responses：这条路径带 opencode 兜底，WorkBuddy 429 时仍能拿到文本
  $body = @{ model = $need; stream = $false; input = 'reply with OK only' } | ConvertTo-Json -Depth 5
  try {
    $r = Invoke-RestMethod 'http://127.0.0.1:8790/v1/responses' -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 180
    $text = $r.output[0].content[0].text
  } catch { $text = 'CALL_ERR:' + $_.Exception.Message }
}
$textLen = 0
$textOk = $false
$errTag = 'none'
if ($text) {
  if ($text -match '^(CALL_ERR|MODELS_ERR)') { $errTag = $Matches[1] } else { $textOk = $true; $textLen = $text.Length }
}
$line = "HIT 8788=$(PortUp 8788) 4097=$(PortUp 4097) 8792=$(PortUp 8792) 8790=$(PortUp 8790) models=$models deepseek=$modelOk catalog=$has text_ok=$textOk textlen=$textLen err=$errTag"
$line.Substring(0, [Math]::Min(400, $line.Length))
