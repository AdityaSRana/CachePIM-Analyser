@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo CachePIM: Architectural Exploration Platform (Windows)
echo ==========================================================

rem Check if Python is accessible
call "%~dp0python.bat" --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python 3.10+ is required to run CachePIM.
    echo Please install Python from https://www.python.org/ and check "Add Python to PATH".
    pause
    exit /b 1
)

rem Check if streamlit is installed
call "%~dp0python.bat" -m streamlit --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Streamlit is not yet installed in this environment.
    echo [INFO] Installing required packages from requirements.txt...
    call "%~dp0python.bat" -m pip install -r "%~dp0requirements.txt"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies. Please run setup.bat first.
        pause
        exit /b 1
    )
)

echo [INFO] Starting CachePIM Dashboard on http://localhost:8505...
call "%~dp0streamlit.bat" run "%~dp0app.py" %*

pause
