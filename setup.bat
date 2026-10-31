@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo CachePIM: One-Click Environment Setup (Windows)
echo ==========================================================

rem 1. Locate Python executable
set PYTHON_CMD=
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_CMD=python"
    ) else (
        where python3 >nul 2>nul
        if %ERRORLEVEL% equ 0 (
            set "PYTHON_CMD=python3"
        )
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python 3 was not found in your system PATH.
    echo Please install Python 3.10 or higher from https://www.python.org/
    echo Make sure to check the option "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [INFO] Detected system Python:
%PYTHON_CMD% --version

rem 2. Create virtual environment if missing or broken
set "RECREATE_VENV=0"
if not exist "%~dp0.venv\Scripts\python.exe" (
    set "RECREATE_VENV=1"
) else (
    "%~dp0.venv\Scripts\python.exe" -c "import sys" >nul 2>nul
    if errorlevel 1 set "RECREATE_VENV=1"
)

if "%RECREATE_VENV%"=="1" (
    echo [INFO] Creating clean virtual environment at .venv ...
    if exist "%~dp0.venv" (
        echo [INFO] Removing stale or non-portable virtual environment...
        rmdir /s /q "%~dp0.venv" 2>nul
    )
    %PYTHON_CMD% -m venv "%~dp0.venv"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Healthy virtual environment found at .venv.
)

rem 3. Upgrade pip and install dependencies
echo [INFO] Upgrading pip...
"%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip

echo [INFO] Installing dependencies from requirements.txt...
"%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Encountered an error installing requirements.
    pause
    exit /b 1
)

echo.
echo ==========================================================
echo [SUCCESS] CachePIM environment setup completed!
echo To run the dashboard, double-click run_dashboard.bat
echo ==========================================================
pause
