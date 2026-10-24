# Shared JSONL logger for PowerShell scripts (same schema as lib/log.mjs)
# Usage:
#   . (Join-Path $PSScriptRoot '..\lib\wlog.ps1')      # from scripts\
#   Write-Log -Comp launcher -Level info -Msg 'start-all.begin' -Extra @{ ports = '8788,4097,8792,8790' }

$script:WbaLogDir = if ($env:WBA_LOG_DIR) { $env:WBA_LOG_DIR } else { Join-Path (Split-Path -Parent $PSScriptRoot) 'logs' }
if ($PSScriptRoot -like '*\scripts' -or $PSScriptRoot -like '*\dev') {
  $script:WbaLogDir = if ($env:WBA_LOG_DIR) { $env:WBA_LOG_DIR } else { Join-Path (Split-Path -Parent $PSScriptRoot) 'logs' }
}
$script:WbaLogMax = if ($env:WBA_LOG_MAX) { [int]$env:WBA_LOG_MAX } else { 5MB }

function Get-WbaLogPath([string]$Comp) {
  if (-not (Test-Path $script:WbaLogDir)) { New-Item -ItemType Directory -Force -Path $script:WbaLogDir | Out-Null }
  return Join-Path $script:WbaLogDir ("" + $Comp + ".log")
}

function Invoke-LogRotate([string]$path) {
  if (-not (Test-Path $path)) { return }
  if ((Get-Item $path).Length -lt $script:WbaLogMax) { return }
  $old = [IO.Path]::ChangeExtension($path, $null) + '1.log'
  if (Test-Path $old) { Remove-Item $old -Force }
  Move-Item $path $old -Force
}

function Write-Log {
  param(
    [string]$Comp = 'launcher',
    [ValidateSet('debug', 'info', 'warn', 'error')][string]$Level = 'info',
    [string]$Msg = '',
    [hashtable]$Extra = @{}
  )
  $path = Get-WbaLogPath $Comp
  Invoke-LogRotate $path
  $rec = [ordered]@{
    ts    = (Get-Date).ToUniversalTime().ToString('o')
    level = $Level
    comp  = $Comp
    msg   = $Msg
  }
  foreach ($k in $Extra.Keys) {
    $v = $Extra[$k]
    if ($null -eq $v) { continue }
    $rec[$k] = $v
  }
  try {
    ($rec | ConvertTo-Json -Compress) | Add-Content -Path $path -Encoding utf8
  } catch { }
  if ($env:WBA_LOG_STDERR -eq '1') { ($rec | ConvertTo-Json -Compress) | Write-Host }
}

function if_ok([bool]$ok) { if ($ok) { return 'info' } else { return 'warn' } }