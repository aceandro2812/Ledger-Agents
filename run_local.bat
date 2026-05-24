@echo off
title Forensic Audit Launcher

echo ==================================================
echo   GL Ledger Forensic Audit Suite Launcher
echo ==================================================
echo.

REM Check if backend requirements are installed
if not exist "backend\venv" (
    echo [System] Creating Python virtual environment in backend/venv...
    python -m venv backend\venv
    if %errorlevel% neq 0 (
        echo [Error] Python is not installed or not in PATH. Please install Python 3.11+.
        pause
        exit /b 1
    )
)

echo [System] Activating virtual environment and verifying dependencies...
call backend\venv\Scripts\activate
pip install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo [Error] Failed to install backend dependencies.
    pause
    exit /b 1
)

REM Check if frontend node_modules is installed
if not exist "frontend\node_modules" (
    echo [System] Installing frontend npm dependencies...
    cd frontend
    call npm install
    cd ..
    if %errorlevel% neq 0 (
        echo [Error] Node.js is not installed or npm failed. Please install Node.js 18+.
        pause
        exit /b 1
    )
)

echo.
echo [System] Launching Backend Server on port 8000...
start cmd /k "title Forensic Audit Backend && call backend\venv\Scripts\activate && set PYTHONPATH=.&& uvicorn backend.main:app --reload --port 8000"

echo [System] Launching Frontend Dev Server on port 5173...
start cmd /k "title Forensic Audit Frontend && cd frontend && npm run dev"

echo.
echo [Success] Both servers started in separate windows!
echo - API server: http://localhost:8000
echo - Web interface: http://localhost:5173
echo.
pause
