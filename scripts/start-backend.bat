@echo off
setlocal
cd /d "%~dp0.."
if not exist "backend\app\main.py" (
  echo [ERROR] 找不到 backend\app\main.py
  pause
  exit /b 1
)
if not exist "backend\.venv\Scripts\python.exe" (
  echo [ERROR] 找不到 backend\.venv，请先创建虚拟环境并安装依赖
  pause
  exit /b 1
)
cd /d "%~dp0..\backend"
echo 毕设港 API → http://127.0.0.1:8000
"%~dp0..\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
