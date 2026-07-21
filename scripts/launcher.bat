@echo off
setlocal
chcp 65001 >nul
title Gate Launcher
rem Prefer Windows Terminal so service starts can open as sibling tabs.
rem If already inside wt (WT_SESSION) or wt missing, run PowerShell in this window.
if defined WT_SESSION goto :run
where wt >nul 2>nul
if errorlevel 1 goto :run
wt -d "%~dp0.." --title "Gate Console" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1"
exit /b 0
:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1"
exit /b %ERRORLEVEL%
