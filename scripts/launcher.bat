@echo off
setlocal
chcp 65001 >nul
title Gate Launcher
rem GF_WT_WINDOW must match scripts/_backend-procs.ps1 ($script:GfWtWindow default).
set "GF_WT_WINDOW=gf-gate"
rem Interactive (no args): prefer named WT window for console + service tabs.
rem CLI args (launcher.bat 1): stay in current console so output is visible.
rem Already inside wt (WT_SESSION) or wt missing: run here.
if not "%~1"=="" goto :run
if defined WT_SESSION goto :run
where wt >nul 2>nul
if errorlevel 1 goto :run
wt -w %GF_WT_WINDOW% --title "Gate Console" -d "%~dp0.." -- powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1"
exit /b 0
:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1" %*
exit /b %ERRORLEVEL%
