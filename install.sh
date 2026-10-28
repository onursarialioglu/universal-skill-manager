#!/usr/bin/env bash
set -e

echo "========================================================"
echo "   Universal Skill Manager (USM) - Unix Installer"
echo "========================================================"
echo

# 1. Check Python
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "[ERROR] Python 3.10+ is required but not found!"
    exit 1
fi

$PYTHON_BIN -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" || {
    echo "[ERROR] Python 3.10 or higher is required."
    $PYTHON_BIN --version
    exit 1
}

echo "[1/4] Found Python: $($PYTHON_BIN --version)"

# 2. Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[2/4] Creating virtual environment (.venv)..."
    $PYTHON_BIN -m venv .venv
else
    echo "[2/4] Virtual environment already exists (.venv)."
fi

# 3. Install Package
echo "[3/4] Installing Universal Skill Manager and dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

# 4. Verification
echo "[4/4] Verifying installation..."
usm status

echo
echo "========================================================"
echo "   Installation Successful!"
echo "========================================================"
echo
echo "Quick commands:"
echo "  - Activate venv:          source .venv/bin/activate"
echo "  - Start Web UI:           ./start_usm.sh (or 'usm ui')"
echo "  - Configure AI Agents:    usm setup-agent"
echo "  - List Skills:            usm list"
echo "  - CLI Help:               usm --help"
echo
