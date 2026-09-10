@echo off
setlocal enabledelayedexpansion
title MAST Topology Lab - Local Launcher

echo ==========================================================================
echo   🔬 MAST Topology Lab - Single-Click Windows Launcher
echo ==========================================================================

cd /d "%~dp0"

:: 1. Pre-flight checks
echo [1/5] Checking prerequisites...

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in system PATH.
    echo Please install Python 3.10+ and retry.
    pause
    exit /b 1
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in system PATH.
    echo Please install Node.js 18+ and retry.
    pause
    exit /b 1
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] npm is not installed or not in system PATH.
    pause
    exit /b 1
)

:: 2. Virtual Environment Setup
echo [2/5] Setting up Python virtual environment...
if not exist ".venv" (
    echo   Creating Python virtual environment in .venv ...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo   Installing/Verifying Python dependencies...
python -m pip install -q --upgrade pip
python -m pip install -q -r backend\requirements.txt

:: 3. Backend Environment Config Check
echo [3/5] Checking backend configuration...
if not exist "backend\.env" (
    echo   backend\.env not found. Creating default from backend\.env.example ...
    copy backend\.env.example backend\.env >nul
)

:: 4. Frontend Package Setup
echo [4/5] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo   frontend\node_modules not found. Running npm install...
    cd frontend
    call npm install
    cd ..
)

:: 5. Launch Services
echo [5/5] Launching backend & frontend services...

echo Starting FastAPI Backend server on http://127.0.0.1:8000 ...
start "MAST Backend" cmd /k "cd backend && ..\.venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo Starting React/Vite Frontend server on http://localhost:5173 ...
start "MAST Frontend" cmd /k "cd frontend && npm run dev"

timeout /t 3 >nul

echo.
echo ==========================================================================
echo   🚀 MAST Topology Lab is live!
echo ==========================================================================
echo   🌐 Frontend Dashboard: http://localhost:5173
echo   ⚙️  Backend REST API:  http://127.0.0.1:8000
echo   📖 Swagger API Docs:  http://127.0.0.1:8000/docs
echo.
echo Close the opened Backend and Frontend windows to stop the servers.
echo ==========================================================================

start http://localhost:5173
