# Script to build and package Ledger Forensic Audit application as a single Windows executable.

# Terminate any running instances of the app to release file handles
taskkill /f /im LedgerForensicAudit.exe 2>$null | Out-Null

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Building React Frontend..." -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

Push-Location frontend
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Frontend build failed. Exiting."
    Pop-Location
    exit $LASTEXITCODE
}
Pop-Location

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "Packaging Application with PyInstaller..." -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Define python executable path from virtual environment
$python_exe = ".\backend\venv\Scripts\python.exe"
$pyinstaller_exe = ".\backend\venv\Scripts\pyinstaller.exe"

if (-not (Test-Path $pyinstaller_exe)) {
    Write-Host "Installing pyinstaller in the virtual environment..." -ForegroundColor Yellow
    & $python_exe -m pip install pyinstaller
}

# Run PyInstaller
# Note: we use --add-data "frontend/dist;dist" on Windows to copy built frontend assets into the EXE.
# We use --noconsole to hide the terminal window since we are using pywebview for a native window.
# We also include --hidden-import for tiktoken extensions which are dynamically loaded at runtime.
& $pyinstaller_exe --onefile --noconsole --name="LedgerForensicAudit" --add-data "frontend/dist;dist" --hidden-import="tiktoken_ext" --hidden-import="tiktoken_ext.openai_public" desktop_launcher.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller packaging failed."
    exit $LASTEXITCODE
}

Write-Host "`n==================================================" -ForegroundColor Green
Write-Host "SUCCESS: Application packaged successfully!" -ForegroundColor Green
Write-Host "Executable location: .\dist\LedgerForensicAudit.exe" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

