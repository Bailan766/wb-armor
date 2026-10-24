param(
  [int]$Tail = 20,
  [string]$Grep,
  [string]$Session,
  [string]$Comp,
  [ValidateSet('debug','info','warn','error')][string]$Level,
  [int]$Since = 0,
  [switch]$Stats,
  [switch]$Files,
  [int]$Prune = 0,
  [switch]$Json
)
$ErrorActionPreference = 'SilentlyContinue'
$Root = Split-Path -Parent $PSScriptRoot
$LogDir = if ($env:WBA_LOG_DIR) { $env:WBA_LOG_DIR } else { Join-Path $Root 'logs' }

if ($Files) {
  Get-ChildItem $LogDir -Filter *.log | Sort-Object LastWriteTime -Descending |
    Select-Object Name, @{n = 'KB'; e = { [int]($_.Length / 1KB) } }, LastWriteTime | Format-Table -AutoSize
  return
}

if ($Prune -gt 0) {
  $cut = (Get-Date).AddDays(-$Prune)
  $old = Get-ChildItem $LogDir -Filter *.log | Where-Object { $_.LastWriteTime -lt $cut }
  $n = 0
  foreach ($f in $old) { Remove-Item $f.FullName -Force; $n++ }
  "PRUNED removed=$n olderThan=$($cut.ToString('s'))"
  return
}

$rows = @()
foreach ($f in (Get-ChildItem $LogDir -Filter *.log | Sort-Object LastWriteTime)) {
  foreach ($line in (Get-Content $f.FullName -Tail 5000)) {
    if (-not $line.Trim()) { continue }
    try { $o = $line | ConvertFrom-Json } catch {
      $rows += [pscustomobject]@{ ts = ''; level = 'raw'; comp = $f.BaseName; msg = $line; extra = '' }
      continue
    }
    $extra = ($o.PSObject.Properties.Name | Where-Object { $_ -notin @('ts','level','comp','msg') } |
      ForEach-Object { "$_=$($o.$_)" }) -join ' '
    $rows += [pscustomobject]@{ ts = $o.ts; level = $o.level; comp = $o.comp; msg = $o.msg; extra = $extra }
  }
}

if ($Comp) { $rows = $rows | Where-Object { $_.comp -eq $Comp } }
if ($Session) { $rows = $rows | Where-Object { $_.extra -match [regex]::Escape($Session) } }
if ($Level) { $rows = $rows | Where-Object { $_.level -eq $Level } }
if ($Grep) { $rows = $rows | Where-Object { ($_.msg + ' ' + $_.extra) -match $Grep } }
if ($Since -gt 0) {
  $cut = (Get-Date).ToUniversalTime().AddMinutes(-$Since)
  $rows = $rows | Where-Object { $_.ts -and ([datetime]$_.ts) -ge $cut }
}

if ($Stats) {
  $err = @($rows | Where-Object { $_.level -eq 'error' }).Count
  $warn = @($rows | Where-Object { $_.level -eq 'warn' }).Count
  $info = @($rows | Where-Object { $_.level -eq 'info' }).Count
  $byComp = $rows | Group-Object comp | ForEach-Object { "$($_.Name)=$($_.Count)" }
  $byMsg = $rows | Where-Object { $_.level -in @('error','warn') } | Group-Object msg |
    Sort-Object Count -Descending | Select-Object -First 5 | ForEach-Object { "$($_.Name)x$($_.Count)" }
  "STATS total=$($rows.Count) info=$info warn=$warn error=$err"
  "  comps: " + ($byComp -join ' ')
  "  top-issues: " + ($byMsg -join ' | ')
  return
}

$rows | Select-Object -Last $Tail | ForEach-Object {
  if ($Json) { $_ | ConvertTo-Json -Compress }
  else { '{0} {1,-5} {2,-4} {3} {4}' -f ($_.ts -replace 'T', ' ' -replace '\.\d+Z', 'Z'), $_.level, $_.comp, $_.msg, $_.extra }
}
