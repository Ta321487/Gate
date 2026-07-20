@echo off
setlocal
chcp 65001 >nul
title Gate Launcher
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1"
exit /b %ERRORLEVEL%