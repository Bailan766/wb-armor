[CmdletBinding()]
param(
  [ValidateSet('gui','up','down','status','restart','patch','restore','verify','selftest','setup','payload','setup-dsh','sync-models')]
  [string]$Action = 'gui',
  [string]$Which = 'flash',
  [switch]$Dsh
)
$ErrorActionPreference = 'Stop'
$R      = $PSScriptRoot
if (-not $R) { $R = Split-Path -Parent $MyInvocation.MyCommand.Path }
$GUI    = Join-Path $R 'gui\wbarmor_gui.py'
$SELF   = Join-Path $R 'dev\selftest.py'
function Resolve-Python {
  foreach ($c in @(
    (Join-Path $GW '.venv\Scripts\python.exe'),
    'C:\Program Files\Python314\python.exe'
  )) { if (Test-Path $c) { return $c } }
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  return $null
}
$GW = Join-Path $R 'gw\workbuddy2api'
$PYPATH = Resolve-Python
$Ports  = 8788,4097,8792,8790
$Tasks  = 'WB8788','OC4097','OCB8792','IG5B8790'
function Port-Up([int]$p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }
function Show-Status {
  $allUp = $true
  foreach ($p in $Ports) { $u = Port-Up $p; if (-not $u) { $allUp = $false }; Write-Host ('  port {0} => {1}' -f $p, $u) }
  try {
    $h = Invoke-RestMethod -Uri 'http://127.0.0.1:8790/health' -TimeoutSec 4
    Write-Host ('  health ok={0} upstream={1} payload={2} chars' -f $h.ok, $h.upstream, $h.payload_chars)
    Write-Host ('  served={0} fallbacks={1} last_model={2} last_status={3}' -f $h.served, $h.fallbacks, $h.last_model, $h.last_status)
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
  if (-not $found) {
    # 关键：插到第一个 [table] 之前，绝不能追加到文件末尾（会落进最后一个表，导致 TOML 语义错乱、客户端起不来）
    $out = @($out)
    $idx = -1
    for ($i = 0; $i -lt $out.Count; $i++) { if ($out[$i] -match '^\s*\[') { $idx = $i; break } }
    $line = '{0} = "{1}"' -f $key, $value
    if ($idx -ge 0) { $out = @($out[0..($idx - 1)] + $line + $out[$idx..($out.Count - 1)]) }
    else { $out = @($out) + $line }
  }
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
  # seed catalog from bundled sample if missing（样本在 config\，兼容旧版根目录）
  if (-not (Test-Path $cat)) {
    $src = @(
      (Join-Path $R 'config\ig5-model-catalog.sample.json'),
      (Join-Path $R 'ig5-model-catalog.sample.json')
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($src) { Copy-Item $src $cat -Force; 'catalog seeded from sample' }
    else { 'sample catalog missing (config\ig5-model-catalog.sample.json)' }
  }
  else { 'catalog present' }
  # apply armor to client side (base_instructions in catalog) via generator
  $gen = @(
    (Join-Path $R 'scripts\generate-client-armor.py'),
    (Join-Path $R 'generate-client-armor.py')
  ) | Where-Object { Test-Path $_ } | Select-Object -First 1
  if ($gen -and $PYPATH) { & $PYPATH $gen --codex-only }
  elseif (-not $gen) { 'generator missing (scripts\generate-client-armor.py)' }
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

function Sync-Models {
  $cat = Join-Path $env:USERPROFILE '.codex\ig5-model-catalog.json'
  $live = $null
  try { $live = Invoke-RestMethod -Uri 'http://127.0.0.1:8790/v1/models' -TimeoutSec 8 } catch { }
  $ids = @()
  if ($live -and $live.data) { $ids = @($live.data | ForEach-Object { $_.id }) }
  if ($ids.Count -eq 0) { Write-Host 'models endpoint unreachable (8790) - nothing written'; return }
  $tplPath = @($cat, (Join-Path $R 'config\ig5-model-catalog.sample.json')) | Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $tplPath) { Write-Host 'catalog template missing'; return }
  $tpl = Get-Content -LiteralPath $tplPath -Raw -Encoding utf8 | ConvertFrom-Json
  $base = @($tpl.models)[0]
  $free = @('deepseek-v4.1-flash-free','glm-5.3-flash-free','mimo-v2.6-flash-free','nemotron-3-ultra-free','nemotron-3.5-lightning-free','nemotron-3.5-super-vl-free','flint-40b-free','beam-free','big-pickle')
  $rows = @()
  foreach ($id in $ids) { $rows += [pscustomobject]@{ slug = $id; label = ('WorkBuddy - ' + $id); pri = 1000 } }
  foreach ($f in $free) { $rows += [pscustomobject]@{ slug = ('oc-' + $f); label = ('opencode - ' + $f); pri = 800 } }
  $seen = @{}
  $models = @()
  foreach ($m in ($rows | Sort-Object @{ Expression = { if ($_.slug -eq 'deepseek-v4.1-flash') { 0 } else { 1 } } }, @{ Expression = { - $_.pri } })) {
    if ($seen.ContainsKey($m.slug)) { continue }
    $seen[$m.slug] = 1
    $o = $base.PSObject.Copy()
    $o.slug = $m.slug
    $o.display_name = $m.label
    $o.description = $m.label
    $o.priority = [int]$m.pri
    $models += $o
  }
  if (Test-Path $cat) { Copy-Item $cat ($cat + '.bak') -Force }
  $json = @{ models = $models } | ConvertTo-Json -Depth 8
  # 必须无 BOM：Python 侧 json.load 用 utf-8 读，带 BOM 会直接抛 JSONDecodeError
  [IO.File]::WriteAllText($cat, $json, (New-Object System.Text.UTF8Encoding($false)))
  Write-Host ('catalog synced: {0} models -> {1}' -f $models.Count, $cat)
  Write-Host 'Reload the Codex window to refresh the model picker.'
}

function Stop-Ports { foreach ($pt in 8788,4097,8792,8790) { $own = (Get-NetTCPConnection -LocalPort $pt -State Listen -ErrorAction SilentlyContinue).OwningProcess; if ($own) { Stop-Process -Id $own -Force -ErrorAction SilentlyContinue; Write-Host ('killed port ' + $pt + ' pid ' + $own) } } }

switch ($Action) {
  'up'      { & (Join-Path $R 'scripts\start-all.ps1'); Show-Status | Out-Null }
  'down'    { foreach ($t in $Tasks) { schtasks /End /TN $t 2>$null | Out-Null }; Stop-Ports; 'stopped tasks + port owners' }
  'status'  { Show-Status | Out-Null }
  'restart' { foreach ($t in $Tasks) { schtasks /End /TN $t 2>$null | Out-Null }; Stop-Ports; Start-Sleep 2; & (Join-Path $R 'scripts\start-all.ps1'); Show-Status | Out-Null }
  'patch'   { & (Join-Path $R 'scripts\patch-armor.ps1') -Mode patch; & (Join-Path $R 'scripts\verify.ps1') }
  'restore' { & (Join-Path $R 'scripts\patch-armor.ps1') -Mode restore }
  'verify'  { & (Join-Path $R 'scripts\verify.ps1') }
  'selftest'{ if (-not $PYPATH -or -not (Test-Path $SELF)) { Write-Host ('selftest skipped (python=' + $PYPATH + ', script=' + $SELF + ')'); exit 0 }; & $PYPATH $SELF; exit $LASTEXITCODE }
  'setup'   { Setup-Codex; if ($Dsh) { & (Join-Path $R 'scripts\setup-dsh.ps1') } }
  'payload' { Set-Payload $Which }
  'setup-dsh' { & (Join-Path $R 'scripts\setup-dsh.ps1') }
  'sync-models' { Sync-Models }
  'open' { & (Join-Path $R 'scripts\open-codex.ps1') }
  'fix-codex' { & (Join-Path $R 'scripts\fix-codex.ps1') }
  'gui' {
    & (Join-Path $R 'scripts\start-all.ps1') | Out-Null
    & (Join-Path $R 'gui\launch-gui.ps1')
    Show-Status | Out-Null
  }
  default   { Write-Host ('unknown action: ' + $Action) }
}
