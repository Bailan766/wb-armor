@echo off
rem wb-armor 2.0 - one click: start services (if needed) + open the control panel
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch-app.ps1"
if errorlevel 2 (
  echo.
  echo python not found in PATH - install Python 3.10+ first.
  pause
)
endlocal
