@echo off
rem CachePIM Cross-Device Streamlit Wrapper (Windows)
if exist "%~dp0.venv\Scripts\streamlit.exe" (
    "%~dp0.venv\Scripts\streamlit.exe" %*
) else (
    call "%~dp0python.bat" -m streamlit %*
)
