# Script to build and package Ledger Forensic Audit application as a single Windows executable.

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
# We keep the console window open to allow users to see logs and easily shut down the app.
& $pyinstaller_exe --onefile --name="LedgerForensicAudit" --add-data "frontend/dist;dist" desktop_launcher.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller packaging failed."
    exit $LASTEXITCODE
}

Write-Host "`n==================================================" -ForegroundColor Green
Write-Host "SUCCESS: Application packaged successfully!" -ForegroundColor Green
Write-Host "Executable location: .\dist\LedgerForensicAudit.exe" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
