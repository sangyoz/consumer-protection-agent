@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" -Action stop
set "result=%errorlevel%"
if not "%result%"=="0" pause
exit /b %result%
