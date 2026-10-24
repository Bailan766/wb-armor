# launch-gui.ps1 - one-shot launcher (kept for backwards compat)
# Delegates to wbarmor.ps1 gui (ensures services -> selftest -> pythonw GUI).
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'wbarmor.ps1') gui
