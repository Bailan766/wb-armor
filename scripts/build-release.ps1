param([switch]$SkipExe)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Root 'package.json'))) { $Root = $PSScriptRoot }
$pkg = Get-Content (Join-Path $Root 'package.json') -Raw | ConvertFrom-Json
$ver = $pkg.version
$stage = Join-Path $Root ("dist\wb-armor-$ver")
$zip = Join-Path $Root ("dist\wb-armor-$ver.zip")
$notes = Join-Path $Root ("dist\wb-armor-$ver\RELEASE-NOTES.md")

Write-Host "== build release $ver =="
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stage | Out-Null

# 1) stage working tree (exclude VCS / venv / dist / caches)
$xd = @('.git','dist','node_modules','.venv','__pycache__','logs')
$xf = @('ig5-debug.log*', '*.log', 'wb-armor.exe')
$args = @($Root, $stage, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/XD') + $xd + @('/XF') + $xf
& robocopy @args | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed: $LASTEXITCODE" }
# 3) optional prebuilt launcher
if (-not $SkipExe) {
  $exe = Join-Path $Root 'dist\wb-armor.exe'
  if (Test-Path $exe) {
    New-Item -ItemType Directory -Force -Path (Join-Path $stage 'bin') | Out-Null
    Copy-Item $exe (Join-Path $stage 'bin\wb-armor.exe') -Force
  }
}

# 4) version + notes
Set-Content -Path (Join-Path $stage 'VERSION.txt') -Value $ver -Encoding ascii
$notesLines = @(
  ('# wb-armor ' + $ver),
  '',
  'Contents: src/ (ig5-bridge 8790, opencode-bridge 8792), scripts/ (start, supervisor, armor, verify, dsh setup),',
  'gui/ (tk console), config/ (catalog + dsh patch samples), dev/ (doctor, repair, fix-window, probe-tools), bin/ (optional exe).',
  '',
  'Install:',
  '  1) unzip to any ASCII path',
  '  2) requires Python 3.10+, Node 18+, opencode CLI',
  '  3) first run: python -m wbarmor deploy-codex   (and deploy-dsh for DSH)',
  '  4) start: 启动.cmd  (or python -m wbarmor start)',
  '',
  'Fixes in 1.0.1:',
  '  - launcher recursion + wrong paths (gui/selftest.py, start-all.ps1)',
  '  - DSH headless profile was empty (401); added /v1/messages + Anthropic SSE fallback',
  '  - free-tier session reuse caused 98k tokens per call -> new session per request',
  '  - strip zero-width chars from model output',
  '  - sync-models wrote UTF-8 BOM -> Python JSONDecodeError',
  '  - scheduled tasks pointed at moved files (WB8788 / WBSupervisor / OCB8792 / IG5B8790)'
)
$notesLines | Set-Content -Path $notes -Encoding utf8


# 5) manifest
$files = Get-ChildItem $stage -Recurse -File | Where-Object { $_.Name -ne 'MANIFEST.sha256' }
$lines = foreach ($f in $files) {
  $h = (Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower()
  '{0}  {1}' -f $h, $f.FullName.Substring($stage.Length + 1).Replace('\', '/')
}
$lines | Set-Content -Path (Join-Path $stage 'MANIFEST.sha256') -Encoding ascii

# 6) zip
if (Test-Path $zip) { Remove-Item $zip -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($stage, $zip, [IO.Compression.CompressionLevel]::Optimal, $false)
$zipInfo = Get-Item $zip
$zipHash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()

'RELEASE {0} files={1} zip={2}MB sha256={3}' -f $ver, (($files.Count) + 1), [math]::Round($zipInfo.Length / 1MB, 2), $zipHash
