# launch-gui.ps1 - thin forwarder kept for backwards compatibility.
# IMPORTANT: do NOT call wbarmor.ps1 gui here (that action invokes this file -> infinite loop).
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& (Join-Path $root 'gui\launch-gui.ps1')
