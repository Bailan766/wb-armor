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

# 1) export only committed files (git archive), so the package matches the tag
$tmp = Join-Path $env:TEMP ("wbarmor-$ver-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
Push-Location $Root
& git archive --format=tar HEAD | tar -x -C $tmp
Pop-Location

# 2) copy staged tree
Copy-Item (Join-Path $tmp '*') $stage -Recurse -Force
Remove-Item $tmp -Recurse -Force

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
@"
# wb-armor $ver

## 内容
- `src/` 两个桥：`ig5-bridge.mjs`（8790，路由/载荷/兜底/事件流）、`opencode-bridge.mjs`（8792，免费档外壳）
- `scripts/` 启动、自愈、破甲、校验、DSH 配置脚本
- `gui/` Tk 控制台（Python 3.10+）
- `config/` 模型目录样本、DSH patch 样本
- `dev/` 排障件：doctor / repair / fix-window / probe-tools
- `bin/wb-armor.exe` 预打包启动器（可选，需能写 %TEMP%）

## 安装
1. 解压到任意目录（路径不要含中文）。
2. 需要 Python 3.10+、Node 18+、opencode CLI。
3. 首次：`.\wbarmor.ps1 setup -Dsh`（配置 Codex 与 DSH 指向本地桥）。
4. 启动：双击 `启动.cmd` 或 `.\wbarmor.ps1 gui`。

## 本版修复
- 启动链递归与三处错误路径（`gui\selftest.py`、`start-all.ps1`）
- DSH headless profile 空白配置导致 401；新增 `/v1/messages` 与 Anthropic SSE 兜底
- 免费档会话复用导致 token 累积（98k/句）→ 改为每请求新会话
- 输出零宽字符 `\u200b` 清洗
- `sync-models` 写入 BOM 导致 Python 侧 JSONDecodeError
- 计划任务指向被移动文件（`WB8788`/`WBSupervisor`/`OCB8792`/`IG5B8790`）
"@ | Set-Content -Path $notes -Encoding utf8

# 5) manifest
$files = Get-ChildItem $stage -Recurse -File | Where-Object { $_.Name -ne 'MANIFEST.sha256' }
$lines = foreach ($f in $files) {
  $h = (Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower()
  '{0}  {1}' -f $h, $f.FullName.Substring($stage.Length + 1).Replace('\', '/')
}
$lines | Set-Content -Path (Join-Path $stage 'MANIFEST.sha256') -Encoding ascii

# 6) zip
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -CompressionLevel Optimal
$zipInfo = Get-Item $zip
$zipHash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()

'RELEASE {0} files={1} zip={2}MB sha256={3}' -f $ver, (($files.Count) + 1), [math]::Round($zipInfo.Length / 1MB, 2), $zipHash
