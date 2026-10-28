@echo off
title Universal Skill Manager Dashboard
cd /d "%~dp0"

echo ===================================================
echo   Universal Skill Manager (USM)
echo   Starting Local Web Dashboard...
echo ===================================================
echo.

if exist ".venv\Scripts\usm.exe" (
    ".venv\Scripts\usm.exe" ui --port 8765
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m usm ui --port 8765
) else (
    usm ui --port 8765
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] An error occurred while starting USM Dashboard.
    echo Make sure you ran install.bat first.
    pause
)
