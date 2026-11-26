@echo off
setlocal
set "GF_PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
"%SystemRoot%\System32\chcp.com" 65001 >nul
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
rem Compact remote size 52x36 (buffer=window, no scrollbar). Older wt may ignore --size.
wt -w %GF_WT_WINDOW% --size 52,36 --title "Gate Console" -d "%~dp0.." -- "%GF_PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1"
exit /b 0
:run
"%GF_PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1" %*
exit /b %ERRORLEVEL%
