@echo off
setlocal
REM Stop backend: kill all uvicorn for this repo (alias of kill-dup /all)
call "%~dp0kill-dup-backend.bat" /all
exit /b %ERRORLEVEL%
