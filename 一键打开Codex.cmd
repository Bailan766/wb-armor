@echo off
rem One-click: repair Codex config (absolute model_catalog_json) then launch Codex
setlocal
set "PS=powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\open-codex.ps1""
%PS%
if errorlevel 1 (
  echo.
  echo FAILED - see messages above.
  pause
)
endlocal
