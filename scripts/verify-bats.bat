@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify-bats.ps1"
exit /b %ERRORLEVEL%
