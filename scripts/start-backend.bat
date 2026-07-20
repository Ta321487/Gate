@echo off
setlocal
cd /d "%~dp0.."
if not exist "backend\app\main.py" (
  echo [ERROR] missing backend\app\main.py
  pause
  exit /b 1
)
if not exist "backend\.venv\Scripts\python.exe" (
  echo [ERROR] missing backend\.venv - create venv and install deps first
  pause
  exit /b 1
)
call "%~dp0kill-dup-backend.bat" /all
cd /d "%~dp0..\backend"
echo Gate API - http://127.0.0.1:8000
"%~dp0..\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-use-colors
pause