@echo off
title AIS-42 HealthOutreach Setup
echo ========================================================
echo   AIS-42 HealthOutreach: Automated Teammate Setup
echo ========================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment (.venv)...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo [2/3] Upgrading pip...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo [3/3] Installing dependencies...
pip install -r backend\requirements.txt

echo.
echo ========================================================
echo   SETUP COMPLETE!
echo   You can now run "start_demo.bat" or "powershell .\start_demo.ps1"
echo ========================================================
pause
