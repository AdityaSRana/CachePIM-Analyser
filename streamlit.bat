@echo off
rem CachePIM Cross-Device Streamlit Wrapper (Windows)
set "VENV_STREAMLIT=%~dp0.venv\Scripts\streamlit.exe"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if exist "%VENV_STREAMLIT%" (
    "%VENV_PY%" -c "import streamlit" >nul 2>nul
    if not errorlevel 1 (
        "%VENV_STREAMLIT%" %*
        exit /b %ERRORLEVEL%
    )
)
call "%~dp0python.bat" -m streamlit %*
