param([switch]$NoFix)
# One-click opener: repair config -> verify -> launch Codex (MSIX) -> check window
$ErrorActionPreference = 'SilentlyContinue'
$Root = Split-Path -Parent $PSScriptRoot
$cfg = Join-Path $env:USERPROFILE '.codex\config.toml'
$AUMID = 'OpenAI.Codex_2p2nqsd0c76g0!App'

# 1) repair model_catalog_json (must be absolute) + provider block
$fix = Join-Path $Root 'scripts\fix-codex.ps1'
if (Test-Path $fix) {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $fix | ForEach-Object { "  " + $_ }
}

# 2) verify TOML parses and catalog path is absolute
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($py -and (Test-Path $cfg)) {
  $chk = Join-Path $env:TEMP 'wbarmor-tomlcheck.py'
  @'
import sys, os, tomllib
d = tomllib.load(open(sys.argv[1], "rb"))
c = d.get("model_catalog_json", "")
print("CONFIG ok provider=%s model=%s abs=%s" % (d.get("model_provider"), d.get("model"), os.path.isabs(c)))
'@ | Set-Content -Path $chk -Encoding utf8
  & $py $chk $cfg
}

# 3) launch
$before = @(Get-Process ChatGPT -ErrorAction SilentlyContinue).Count
Start-Process 'explorer.exe' -ArgumentList ('shell:AppsFolder\' + $AUMID)
$deadline = (Get-Date).AddSeconds(25)
do {
  Start-Sleep -Milliseconds 800
  $p = @(Get-Process ChatGPT -ErrorAction SilentlyContinue)
} while ($p.Count -eq 0 -and (Get-Date) -lt $deadline)

if ($p.Count -eq 0) {
  'LAUNCH fail: ChatGPT.exe not started (try Start-Process explorer.exe shell:AppsFolder\' + $AUMID + ')'
  exit 1
}

"LAUNCH ok pid=$($p[0].Id) procs=$($p.Count) (was $before)"

# 4) off-screen window guard
if (-not $NoFix) {
  $fw = Join-Path $Root 'dev\fix-window.ps1'
  if (Test-Path $fw) { & powershell -NoProfile -ExecutionPolicy Bypass -File $fw | ForEach-Object { "  " + $_ } }
}
