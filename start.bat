@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.10 or newer, then try again.
  pause
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo Node.js and npm were not found. Install Node.js 20.19 or newer, then try again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating the local Python environment...
  python -m venv .venv
  if errorlevel 1 goto :failed
)

echo Checking local Python dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

if not exist "node_modules\vite\bin\vite.js" (
  echo Installing the local React and Vite dependencies...
  call npm install
  if errorlevel 1 goto :failed
)

echo Starting the local PhisLens analysis API...
start "PhisLens API" "%ComSpec%" /k ""%CD%\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log"
echo Starting the PhisLens web interface...
start "PhisLens Web" "%ComSpec%" /k "npm run dev"
timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:5173"
echo PhisLens is running locally. Leave both server windows open while using it.
exit /b 0

:failed
echo Startup failed. Read the message above, then ask for help if needed.
pause
exit /b 1
