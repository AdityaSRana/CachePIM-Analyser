#!/usr/bin/env bash
# CachePIM Cross-Device Dashboard Launcher (macOS / Linux)
set -e

# Navigate to script directory
cd "$(dirname "$0")"

echo "=========================================================="
echo "CachePIM: Architectural Exploration Platform (macOS/Linux)"
echo "=========================================================="

# 1. Detect Python executable
PYTHON_BIN=""
STREAMLIT_BIN=""

if [ -f ".venv/bin/streamlit" ]; then
    STREAMLIT_BIN=".venv/bin/streamlit"
    PYTHON_BIN=".venv/bin/python"
elif [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
    STREAMLIT_BIN=".venv/bin/python -m streamlit"
elif command -v streamlit &>/dev/null; then
    STREAMLIT_BIN="streamlit"
    PYTHON_BIN="python3"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
    STREAMLIT_BIN="python3 -m streamlit"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
    STREAMLIT_BIN="python -m streamlit"
else
    echo "[ERROR] Python 3.10+ was not found in your system PATH."
    echo "Please install Python from https://www.python.org/ or via your package manager:"
    echo "  macOS (Homebrew): brew install python"
    echo "  Ubuntu/Debian:    sudo apt update && sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

echo "[INFO] Using Python: $($PYTHON_BIN --version 2>&1)"

# 2. Check if streamlit is available
if ! $STREAMLIT_BIN version &>/dev/null; then
    echo "[INFO] Streamlit is not yet installed in this environment."
    echo "[INFO] Installing dependencies from requirements.txt..."
    if [ -f ".venv/bin/pip" ]; then
        .venv/bin/pip install --upgrade pip
        .venv/bin/pip install -r requirements.txt
    elif command -v pip3 &>/dev/null; then
        pip3 install -r requirements.txt
    elif command -v pip &>/dev/null; then
        pip install -r requirements.txt
    else
        echo "[ERROR] pip is not available. Please run ./setup.sh first."
        exit 1
    fi
fi

echo "[INFO] Launching CachePIM Dashboard on http://localhost:8505..."
exec $STREAMLIT_BIN run app.py "$@"
