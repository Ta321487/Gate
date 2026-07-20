@echo off
setlocal
REM Detect duplicate uvicorn backends for this repo and clean them up.
REM   scripts\kill-dup-backend.bat          keep newest 1, kill extras
REM   scripts\kill-dup-backend.bat /all     kill all (clean restart)

set "FLAG="
if /I "%~1"=="/all" set "FLAG=-All"
if /I "%~1"=="--all" set "FLAG=-All"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kill-dup-backend.ps1" %FLAG%
exit /b %ERRORLEVEL%
