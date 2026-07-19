@echo off
setlocal
cd /d "%~dp0.."
if not exist "frontend\package.json" (
  echo [ERROR] 找不到 frontend\package.json
  pause
  exit /b 1
)
cd /d "%~dp0..\frontend"
if not exist "node_modules\vite\package.json" (
  echo 首次运行：npm install …
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install 失败
    pause
    exit /b 1
  )
)
echo 毕设港 UI → http://127.0.0.1:5173
call npm run dev -- --host 127.0.0.1 --port 5173
pause
