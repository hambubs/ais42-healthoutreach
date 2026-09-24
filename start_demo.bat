@echo off
title AIS-42 HealthOutreach Launcher
echo Starting AIS-42 HealthOutreach services...
powershell -ExecutionPolicy Bypass -File "%~dp0start_demo.ps1"
