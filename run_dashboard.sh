#!/usr/bin/env bash
# CachePIM Cross-Device Dashboard Launcher (macOS / Linux)
set -e

# Navigate to script directory
cd "$(dirname "$0")"

echo "=========================================================="
echo "CachePIM: Architectural Exploration Platform (macOS/Linux)"
echo "=========================================================="

NEED_SETUP=0
if [ ! -f ".venv/bin/python" ]; then
    NEED_SETUP=1
else
    if ! .venv/bin/python -c "import streamlit, pandas, numpy, plotly, yaml" &>/dev/null; then
        echo "[INFO] Detected environment change or missing dependencies."
        NEED_SETUP=1
    fi
fi

if [ "$NEED_SETUP" -eq 1 ]; then
    echo "[INFO] Initializing / updating environment via setup.sh..."
    ./setup.sh
fi

echo "[INFO] Launching CachePIM Dashboard on http://localhost:8505..."
exec .venv/bin/streamlit run app.py "$@"
