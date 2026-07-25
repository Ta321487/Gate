@echo off
setlocal
cd /d "%~dp0.."
rem Pass-through: -SkipClean (launcher already killed) / -NoWait
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-backend.ps1" %*
exit /b %ERRORLEVEL%
