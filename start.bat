@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" -Action start -OpenBrowser %*
set "result=%errorlevel%"
if not "%result%"=="0" (
  echo.
  echo Startup failed. Check the error above or .run\logs.
  pause
)
exit /b %result%
