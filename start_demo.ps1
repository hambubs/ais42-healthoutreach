# =====================================================================
# AIS-42 HealthOutreach — one-click demo launcher (Self-healing)
# Run:  powershell -ExecutionPolicy Bypass -File .\start_demo.ps1
# =====================================================================
$root = $PSScriptRoot
$venvPy = "$root\.venv\Scripts\python.exe"

# 1. Check or auto-create virtual environment
if (-not (Test-Path $venvPy)) {
    Write-Host "[!] Virtual environment (.venv) not found. Setting it up automatically..." -ForegroundColor Yellow
    $sysPy = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $sysPy) {
        $sysPy = (Get-Command py -ErrorAction SilentlyContinue).Source
    }
    if (-not $sysPy) {
        Write-Host "[-] ERROR: Python is not installed or not in PATH." -ForegroundColor Red
        Write-Host "    Please install Python 3.10+ from https://www.python.org/downloads/ and check 'Add python.exe to PATH'." -ForegroundColor Yellow
        Read-Host "Press Enter to exit..."
        exit 1
    }
    Write-Host "[+] Found Python at: $sysPy" -ForegroundColor Cyan
    Write-Host "[+] Creating virtual environment (.venv)..." -ForegroundColor Cyan
    & $sysPy -m venv "$root\.venv"

    if (Test-Path "$root\backend\requirements.txt") {
        Write-Host "[+] Installing dependencies from backend\requirements.txt..." -ForegroundColor Cyan
        & "$root\.venv\Scripts\pip.exe" install --upgrade pip
        & "$root\.venv\Scripts\pip.exe" install -r "$root\backend\requirements.txt"
    }
}

$py = $venvPy
if (-not (Test-Path $py)) {
    # Fallback to system python if venv creation failed
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
}

Write-Host "Starting Flask backend + Ops Console (port 5000)..." -ForegroundColor Green
Start-Process -FilePath $py -ArgumentList "app.py" -WorkingDirectory "$root\backend" -WindowStyle Minimized

Write-Host "Starting Streamlit Impact Dashboard (port 8501)..." -ForegroundColor Green
Start-Process -FilePath $py -ArgumentList "-m","streamlit","run","$root\dashboard\app.py","--server.port","8501","--browser.gatherUsageStats","false" -WorkingDirectory $root -WindowStyle Minimized

Write-Host "Waiting for services to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 6
Write-Host "Opening browsers..." -ForegroundColor Green
Start-Process "http://localhost:5000"    # Ops Console (Leaflet)
Start-Process "http://localhost:8501"    # Impact Dashboard (Streamlit)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Ops Console     : http://localhost:5000"
Write-Host " Impact Dashboard: http://localhost:8501"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "To stop: close the two Python windows, or run .\stop_demo.ps1"
