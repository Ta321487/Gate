@echo off
setlocal
rem Deprecated alias of verify-scripts.bat (kept for older notes and keyboard habits).
set "GF_RUN="
"%SystemRoot%\System32\where.exe" /q pwsh >nul 2>nul && set "GF_RUN=pwsh"
if not defined GF_RUN set "GF_RUN=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
"%GF_RUN%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify-bats.ps1" %*
exit /b %ERRORLEVEL%
