@echo off
setlocal
rem Encoding contract gate for scripts\ : .bat pure ASCII, .ps1 UTF-8 with BOM.
rem Prefer pwsh (parses BOM-less files fine, so the gate can repair itself);
rem fall back to the absolute Windows PowerShell 5.1 path.
set "GF_RUN="
"%SystemRoot%\System32\where.exe" /q pwsh >nul 2>nul && set "GF_RUN=pwsh"
if not defined GF_RUN set "GF_RUN=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
"%GF_RUN%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify-scripts.ps1" %*
exit /b %ERRORLEVEL%
