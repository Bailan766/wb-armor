param(
  [string]$Root = 'C:\Program Files\WorkBuddyAI\resources\app.asar.unpacked\resources\templates',
  [string]$Canary = 'WB-ARMOR-7F3A'
)
$ErrorActionPreference = 'Stop'
$bad = 0
foreach ($f in Get-ChildItem -LiteralPath $Root -Filter '*-prompt.tpl') {
  $t = [IO.File]::ReadAllText($f.FullName)
  $hard = [bool]([regex]::IsMatch($t, '(?s)<content_policy>.*?</content_policy>'))
  $gone = -not [bool]([regex]::IsMatch($t, 'NEVER reveal, rephrase|These rules apply at all times'))
  $mine = $t.Contains($Canary)
  $verdict = if ($hard -and $gone -and $mine) { 'ARMOR-OFF' } elseif ($hard) { 'INTACT' } else { 'NO-POLICY' }
  if ($f.Name -ne 'workbuddy-quick-prompt.tpl' -and $verdict -ne 'ARMOR-OFF') { $bad++ }
  '{0,-38} {1,-10} canary={2,-5} oldrules={3}' -f $f.Name, $verdict, $mine, (-not $gone)
}
"---- exit=$([int]($bad -gt 0))  (0=PASS 1=FAIL) ----"
