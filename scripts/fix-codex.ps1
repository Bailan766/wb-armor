param([switch]$DryRun)
# 修复 Codex 26.x 的配置错误：model_catalog_json 必须是绝对路径（AbsolutePathBuf）
$ErrorActionPreference = 'Continue'
$cfg = Join-Path $env:USERPROFILE '.codex\config.toml'
$cat = Join-Path $env:USERPROFILE '.codex\ig5-model-catalog.json'
$catToml = $cat.Replace('\', '/')   # TOML 用正斜杠，免转义

if (-not (Test-Path $cfg)) { "FIX-CODEX config.toml 不存在: $cfg"; exit 2 }

$text = Get-Content $cfg -Raw
$orig = $text
$lines = $text -split "`r?`n"
$out = @()
$seen = $false
$changed = @()

foreach ($l in $lines) {
  if ($l -match '^\s*model_catalog_json\s*=') {
    $seen = $true
    $cur = ($l -split '=', 2)[1].Trim().Trim('"')
    if ($cur -ne $catToml) {
      $out += 'model_catalog_json = "' + $catToml + '"'
      $changed += ("model_catalog_json: '{0}' -> '{1}'" -f $cur, $catToml)
    } else { $out += $l }
    continue
  }
  $out += $l
}

if (-not $seen) {
  # 插到 model = "..." 之后（没有就放文件头）
  $insertAt = 0
  for ($i = 0; $i -lt $out.Count; $i++) { if ($out[$i] -match '^\s*model\s*=') { $insertAt = $i + 1; break } }
  $out = @($out[0..($insertAt - 1)]) + @('model_catalog_json = "' + $catToml + '"') + @($out[$insertAt..($out.Count - 1)])
  $changed += "model_catalog_json: (missing) -> $catToml"
}

$text = ($out -join "`r`n")

# 补 [model_providers.ig5] 块
if ($text -notmatch '(?m)^\[model_providers\.ig5\]') {
  $text = $text.TrimEnd() + "`r`n`r`n[model_providers.ig5]`r`nname = `"IG5 Bridge (local)`"`r`nbase_url = `"http://127.0.0.1:8790/v1`"`r`nwire_api = `"responses`"`r`nrequires_openai_auth = false`r`nexperimental_bearer_token = `"sk-local-ig5`"`r`n"
  $changed += 'added [model_providers.ig5]'
}

# catalog 文件缺失就从样本复制
if (-not (Test-Path $cat)) {
  $sample = Join-Path (Split-Path -Parent $PSScriptRoot) 'config\ig5-model-catalog.sample.json'
  if (Test-Path $sample) {
    Copy-Item $sample $cat -Force
    $changed += "created catalog from sample"
  } else {
    $changed += "catalog file missing (no sample at $sample)"
  }
}

if ($changed.Count -eq 0) {
  "FIX-CODEX nothing to fix (already absolute): $catToml"
} elseif ($DryRun) {
  "FIX-CODEX DRY-RUN would change:"; $changed | ForEach-Object { "  - $_" }
} else {
  Copy-Item $cfg ($cfg + '.bak-fixcodex') -Force
  [IO.File]::WriteAllText($cfg, $text, (New-Object System.Text.UTF8Encoding($false)))
  "FIX-CODEX applied (backup: $cfg.bak-fixcodex)"
  $changed | ForEach-Object { "  - $_" }
}

# 语法校验（有 python 就用 tomllib）
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($py) {
  $tmp = Join-Path $env:TEMP 'wbarmor-tomlcheck.py'
  $code = @'
import sys, os, tomllib
d = tomllib.load(open(sys.argv[1], "rb"))
c = d.get("model_catalog_json", "")
print("toml_ok abs=" + str(os.path.isabs(c)) + " path=" + c)
'@
  Set-Content -Path $tmp -Value $code -Encoding utf8
  $r = & $py $tmp $cfg 2>&1
  "FIX-CODEX verify: " + (($r | Select-Object -Last 1) -join ' ')
} else {
  "FIX-CODEX verify: python 不在 PATH，跳过 tomllib 校验"
}
"FIX-CODEX catalog_exists=" + (Test-Path $cat)
