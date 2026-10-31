#!/usr/bin/env bash
# CachePIM Environment Setup Script (macOS / Linux)
set -e

cd "$(dirname "$0")"

echo "=========================================================="
echo "CachePIM Environment Setup (macOS / Linux)"
echo "=========================================================="

# 1. Detect Python 3
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "[ERROR] Python 3 was not found in your system PATH."
    echo "Please install Python 3.10 or higher:"
    echo "  macOS (Homebrew): brew install python"
    echo "  Ubuntu/Debian:    sudo apt update && sudo apt install python3 python3-venv python3-pip"
    echo "  Fedora/RHEL:      sudo dnf install python3 python3-pip"
    exit 1
fi

echo "[INFO] Detected system Python: $($PYTHON_BIN --version)"

# 2. Create virtual environment if missing or broken
RECREATE_VENV=0
if [ ! -f ".venv/bin/python" ]; then
    RECREATE_VENV=1
else
    if ! .venv/bin/python -c "import sys" &>/dev/null; then
        RECREATE_VENV=1
    fi
fi

if [ "$RECREATE_VENV" -eq 1 ]; then
    echo "[INFO] Creating clean virtual environment at .venv..."
    rm -rf .venv
    $PYTHON_BIN -m venv .venv
else
    echo "[INFO] Healthy virtual environment found at .venv."
fi

# 3. Upgrade pip and install dependencies
echo "[INFO] Upgrading pip in .venv..."
.venv/bin/python -m pip install --upgrade pip

echo "[INFO] Installing requirements from requirements.txt..."
.venv/bin/python -m pip install -r requirements.txt

echo ""
echo "=========================================================="
echo "[SUCCESS] CachePIM environment setup completed!"
echo "To run the dashboard:"
echo "  ./run_dashboard.sh"
echo "Or manually with:"
echo "  source .venv/bin/activate"
echo "  streamlit run app.py"
echo "=========================================================="
