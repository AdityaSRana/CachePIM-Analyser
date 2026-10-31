@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo CachePIM: Architectural Exploration Platform (Windows)
echo ==========================================================

rem 1. Check if virtual environment is valid and functional
set "NEED_SETUP=0"
if not exist "%~dp0.venv\Scripts\python.exe" (
    set "NEED_SETUP=1"
) else (
    "%~dp0.venv\Scripts\python.exe" -c "import streamlit, pandas, numpy, plotly, yaml" >nul 2>nul
    if errorlevel 1 (
        echo [INFO] Detected environment change or missing dependencies.
        set "NEED_SETUP=1"
    )
)

if "%NEED_SETUP%"=="1" (
    echo [INFO] Initializing / updating environment via setup.bat...
    call "%~dp0setup.bat"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Setup failed. Please ensure Python 3.10+ is installed and on your PATH.
        pause
        exit /b 1
    )
)

echo [INFO] Starting CachePIM Dashboard on http://localhost:8505...
call "%~dp0streamlit.bat" run "%~dp0app.py" %*

pause
