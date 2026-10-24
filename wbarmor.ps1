[CmdletBinding()]
param(
  [ValidateSet('gui','up','down','status','restart','patch','restore','verify','selftest','setup','payload')]
  [string]$Action = 'gui',
  [string]$Which = 'flash'
)
$ErrorActionPreference = 'Stop'
$R      = 'C:\Users\Administrator\Desktop\wb-armor'
$GUI    = Join-Path $R 'gui\wbarmor_gui.py'
$SELF   = Join-Path $R 'gui\selftest.py'
$PYPATH = 'C:\Program Files\Python314\python.exe'
$Ports  = 8788,4097,8792,8790
$Tasks  = 'WB8788','OC4097','OCB8792','IG5B8790'
function Port-Up([int]$p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }
function Show-Status {
  $allUp = $true
  foreach ($p in $Ports) { $u = Port-Up $p; if (-not $u) { $allUp = $false }; Write-Host ('  port {0} => {1}' -f $p, $u) }
  try {
    $h = Invoke-RestMethod -Uri 'http://127.0.0.1:8790/health' -TimeoutSec 4
    Write-Host ('  health ok={0} upstream={1} payload={2} chars' -f $h.ok, $h.upstream, $h.payload_chars)
  } catch { Write-Host '  health unreachable' }
  Write-Host ('  ports_all_up={0}' -f $allUp)
  return $allUp
}
function Set-TomlKV([string]$path, [string]$key, [string]$value) {
  # idempotent top-level key = value
  $lines = if (Test-Path $path) { Get-Content -LiteralPath $path -Encoding utf8 } else { @() }
  $found = $false
  $out = foreach ($l in $lines) {
    if (-not $found -and $l -match ("^\s*" + [regex]::Escape($key) + "\s*=")) {
      $found = $true; ('{0} = "{1}"' -f $key, $value)
    } else { $l }
  }
  if (-not $found) { $out = @($out) + ('{0} = "{1}"' -f $key, $value) }
  Set-Content -Path $path -Value $out -Encoding utf8
}

function Setup-Codex {
  $cfg = Join-Path $env:USERPROFILE '.codex\config.toml'
  $cat = Join-Path $env:USERPROFILE '.codex\ig5-model-catalog.json'
  New-Item -ItemType Directory -Force -Path (Split-Path $cfg) | Out-Null
  if (-not (Test-Path $cfg)) { Set-Content -Path $cfg -Value '' -Encoding utf8 }
  Set-TomlKV $cfg 'model_provider' 'ig5'
  Set-TomlKV $cfg 'model' 'deepseek-v4.1-flash'
  # append [model_providers.ig5] block if missing
  $txt = Get-Content -LiteralPath $cfg -Raw -Encoding utf8
  if ($txt -notmatch '(?m)^\[model_providers\.ig5\]') {
    $txt = $txt.TrimEnd() + "`r`n`r`n[model_providers.ig5]`r`nbase_url = `"http://127.0.0.1:8790/v1`"`r`n"
    Set-Content -Path $cfg -Value $txt -Encoding utf8
    'appended [model_providers.ig5]'
  } else { 'ig5 provider present' }
  # seed catalog from bundled sample if missing
  if (-not (Test-Path $cat)) {
    $src = Join-Path $R 'ig5-model-catalog.sample.json'
    if (Test-Path $src) { Copy-Item $src $cat -Force; 'catalog seeded from sample' }
  }
  else { 'catalog present' }
  # apply armor to client side (base_instructions in catalog) via generator
  $gen = Join-Path $R 'generate-client-armor.py'
  $py = 'C:\Program Files\Python314\python.exe'
  if ((Test-Path $gen) -and (Test-Path $py)) { & $py $gen --codex-only }
  'Codex -> http://127.0.0.1:8790/v1  model=deepseek-v4.1-flash  (provider ig5)'
  'Restart Codex client to apply.'
}

function Set-Payload([string]$which) {
  $map = @{
    flash = 'C:\Users\Administrator\Desktop\dsh-infinite-gen-5-main\prompts\infinite-gen-5.1-flash.md'
    full  = 'C:\Users\Administrator\Desktop\dsh-infinite-gen-5-main\prompts\infinite-gen-5.full.md'
    lazy  = 'C:\Users\Administrator\Desktop\dsh-infinite-gen-5-main\prompts\infinite-gen-5-lazy.md'
  }
  $path = $map[$which]
  if (-not $path -or -not (Test-Path $path)) { Write-Host ('unknown/missing payload: ' + $which); return }
  # 持久化：写进 start-all 启动的进程环境——改为记录到 .payload 供 start-all 读取
  Set-Content -Path (Join-Path $R '.payload') -Value $path -Encoding utf8
  Write-Host ('payload -> ' + $path)
  Write-Host 'restart 桥后生效：wbarmor.ps1 restart'
}

switch ($Action) {
  'up'      { & (Join-Path $R 'start-all.ps1'); Show-Status | Out-Null }
  'down'    { foreach ($t in $Tasks) { schtasks /End /TN $t 2>$null | Out-Null }; 'stopped four tasks' }
  'status'  { Show-Status | Out-Null }
  'restart' { foreach ($t in $Tasks) { schtasks /End /TN $t 2>$null | Out-Null }; Start-Sleep 2; & (Join-Path $R 'start-all.ps1'); Show-Status | Out-Null }
  'patch'   { & (Join-Path $R 'patch-armor.ps1') -Mode patch; & (Join-Path $R 'verify.ps1') }
  'restore' { & (Join-Path $R 'patch-armor.ps1') -Mode restore }
  'verify'  { & (Join-Path $R 'verify.ps1') }
  'selftest'{ & $PYPATH $SELF; exit $LASTEXITCODE }
  'setup'   { Setup-Codex }
  'payload' { Set-Payload $Which }
  'gui' {
    & (Join-Path $R 'start-all.ps1') | Out-Null
    & (Join-Path $R 'gui\launch-gui.ps1')
    Show-Status | Out-Null
  }
  default   { Write-Host ('unknown action: ' + $Action) }
}
