@echo off
rem CachePIM Cross-Device Python Wrapper (Windows)
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        "%VENV_PY%" %*
        exit /b %ERRORLEVEL%
    )
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py -3 %*
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        python %*
    ) else (
        where python3 >nul 2>nul
        if %ERRORLEVEL% equ 0 (
            python3 %*
        ) else (
            echo [ERROR] Python 3 was not found in PATH or in .venv.
            echo Please install Python 3.10+ from https://www.python.org/
            exit /b 1
        )
    )
)
