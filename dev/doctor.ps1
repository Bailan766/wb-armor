param([switch]$Json)
$ErrorActionPreference = 'SilentlyContinue'
$cfg = Join-Path $env:USERPROFILE '.codex\config.toml'
$cat = Join-Path $env:USERPROFILE '.codex\ig5-model-catalog.json'
function P([int]$p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }

$ports = @{}
foreach ($p in 8788, 4097, 8792, 8790) { $ports[$p] = P $p }

$health = $null
try { $health = Invoke-RestMethod 'http://127.0.0.1:8790/health' -TimeoutSec 5 } catch { }

$cfgTxt = if (Test-Path $cfg) { Get-Content $cfg -Raw } else { '' }
$cfgIssues = @()
$lines = $cfgTxt -split "`r?`n"
$curTable = ''
for ($i = 0; $i -lt $lines.Count; $i++) {
  $l = $lines[$i]
  if ($l -match '^\s*\[([^\]]+)\]') { $curTable = $Matches[1]; continue }
  if ($curTable -and $l -match '^\s*(model_provider|model|model_catalog_json|base_url|wire_api)\s*=') {
    $cfgIssues += ('L{0}: {1} inside [{2}]' -f ($i + 1), $l.Trim(), $curTable)
  }
}
$providerBlocks = ([regex]::Matches($cfgTxt, '(?m)^\[model_providers\.')).Count
if ($providerBlocks -eq 0) { $cfgIssues += 'missing [model_providers.*] block' }

$want = ''
if ($cfgTxt -match '(?m)^model\s*=\s*"([^"]+)"') { $want = $Matches[1] }
$catOk = $false; $catModels = 0; $hasModel = $false; $catErr = ''
if (Test-Path $cat) {
  try {
    $j = Get-Content $cat -Raw | ConvertFrom-Json
    $catOk = $true; $catModels = @($j.models).Count
    $hasModel = (@($j.models | Where-Object { $_.slug -eq $want })).Count -gt 0
  } catch { $catErr = $_.Exception.Message }
}

$win = @(Get-Process ChatGPT | Where-Object { $_.MainWindowHandle -ne 0 })
$dup = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*codebuddy_proxy*' }).Count

if ($Json) {
  [pscustomobject]@{
    ports = $ports; health = ($health -ne $null); cfg_issues = $cfgIssues; providers = $providerBlocks
    catalog_ok = $catOk; models = $catModels; catalog_err = $catErr; want_model = $want; model_in_catalog = $hasModel
    app_window = ($win.Count -gt 0); proxy_procs = $dup
  } | ConvertTo-Json -Depth 4
} else {
  'DOCTOR ports 8788={0} 4097={1} 8792={2} 8790={3} health={4} cfg_issues={5} providers={6} catalog={7}/{8} want={9} in_catalog={10} app_window={11} proxy_procs={12}' -f `
    $ports[8788], $ports[4097], $ports[8792], $ports[8790], $(if ($health) { 'ok' } else { 'DOWN' }), $cfgIssues.Count, $providerBlocks, $catOk, $catModels, $want, $hasModel, ($win.Count -gt 0), $dup
  foreach ($i in $cfgIssues) { '  CFG ' + $i }
  if ($catErr) { '  CATALOG ' + $catErr }
}
