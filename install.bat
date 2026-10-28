@echo off
setlocal enabledelayedexpansion

title Universal Skill Manager - Installer
echo ========================================================
echo    Universal Skill Manager (USM) - Windows Installer
echo ========================================================
echo.

:: 1. Check Python installation
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found in PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: 2. Check Python version
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python 3.10 or higher is required.
    python --version
    pause
    exit /b 1
)

echo [1/4] Found Python:
python --version

:: 3. Create Virtual Environment
if not exist ".venv" (
    echo.
    echo [2/4] Creating virtual environment (.venv)...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
) else (
    echo.
    echo [2/4] Virtual environment already exists (.venv).
)

:: 4. Upgrade pip and install package
echo.
echo [3/4] Installing Universal Skill Manager and dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e .
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Package installation failed!
    pause
    exit /b 1
)

:: 5. Self-test and status
echo.
echo [4/4] Verifying installation...
usm status

echo.
echo ========================================================
echo   Installation Successful!
echo ========================================================
echo.
echo Quick commands:
echo   - Start Web UI:           start_usm.bat   (or "usm ui")
echo   - Configure AI Agents:    usm setup-agent
echo   - List Skills:            usm list
echo   - CLI Help:               usm --help
echo.
pause
