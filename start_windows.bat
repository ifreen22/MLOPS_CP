@echo off
echo ========================================================
echo Starting AIOps Sentinel (Windows Native Telemetry Mode)
echo ========================================================
echo.

echo [1/6] Installing backend Python dependencies...
cd backend
pip install -r requirements.txt

echo.
echo [2/6] Generating Prisma Client...
npx prisma generate

echo.
echo [3/6] Pushing Database Schema...
npx prisma db push --accept-data-loss

echo.
echo [4/6] Starting FastAPI Backend...
start cmd /k "python -m uvicorn app.main:app --reload --port 8000"

echo.
echo [5/6] Starting React Frontend...
cd ../aiops-sentinel
call npm install
start cmd /k "npm run dev"

echo.
echo [6/6] Installing and starting the Windows telemetry agent...
cd ..
pip install -r windows-agent-requirements.txt
start "AIOps Sentinel Telemetry Agent" cmd /k "python windows_agent.py"

echo.
echo AIOps Sentinel is now running natively!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.
pause
