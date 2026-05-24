@echo off
title Forensic Audit Standalone Compiler

echo ==================================================
echo   GL Ledger Forensic Audit Suite Standalone Builder
echo ==================================================
echo.

REM 1. Activate backend virtual environment & install requirements
if not exist "backend\venv" (
    echo [System] Creating Python virtual environment...
    python -m venv backend\venv
)
call backend\venv\Scripts\activate
echo [System] Installing python dependencies...
pip install -r backend\requirements.txt
pip install pyinstaller

REM 2. Compile React App frontend
echo [System] Building React frontend application...
if not exist "frontend\node_modules" (
    cd frontend
    call npm install
    cd ..
)
cd frontend
call npm run build
cd ..

if %errorlevel% neq 0 (
    echo [Error] Frontend build failed.
    pause
    exit /b 1
)

REM 3. Package application using PyInstaller
echo [System] Bundling standalone executable...
backend\venv\Scripts\python.exe -m PyInstaller --noconfirm desktop_launcher.spec

if %errorlevel% neq 0 (
    echo [Error] Bundling failed.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo   Standalone executable created: dist\ForensicAudit.exe
echo ==================================================
echo.
pause
