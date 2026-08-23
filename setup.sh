#!/usr/bin/env bash
# setup.sh – Unix port of the original setup.bat

# Enable errexit? We handle checks manually. Use `set -euo pipefail` for safety.
set -euo pipefail

# Change to the directory containing this script
cd "$(dirname "$0")"

# ----------------------------------------------------------------------
# Helper: fail with pause if interactive, then exit 1
# ----------------------------------------------------------------------
fail() {
    echo
    echo "ERROR: $*"
    echo
    if [[ -t 0 ]]; then
        read -r -p "Press any key to continue . . . " -n1
    fi
    exit 1
}

# ----------------------------------------------------------------------
# Locate a suitable Python interpreter (3.9+) and set PYBOOT command
# ----------------------------------------------------------------------
PYBOOT=""

# Check for python3 first (most common on Unix)
if command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
        PYBOOT="python3"
    fi
fi

# If not found, try plain `python`
if [[ -z "$PYBOOT" ]] && command -v python >/dev/null 2>&1; then
    if python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
        PYBOOT="python"
    fi
fi

if [[ -z "$PYBOOT" ]]; then
    if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
        echo "Python was not found on PATH."
        echo "Install Python 3.9+ from https://www.python.org/downloads/"
        echo "Make sure 'python3' or 'python' is available, then re-run setup.sh."
        fail "Python not found"
    else
        fail "Python 3.9+ is required"
    fi
fi

echo "Using bootstrap interpreter: $PYBOOT"

# ----------------------------------------------------------------------
# Verify vendor/worldengine/pyproject.toml exists
# ----------------------------------------------------------------------
if [[ ! -f "vendor/worldengine/pyproject.toml" ]]; then
    echo "vendor/worldengine missing. If you are a maintainer, run:"
    echo "  python scripts/sync_from_dev.py"
    fail "vendor/worldengine/pyproject.toml not found"
fi

# ----------------------------------------------------------------------
# Create virtual environment if needed
# ----------------------------------------------------------------------
if [[ ! -x "venv/bin/python" ]]; then
    echo "Creating venv..."
    "$PYBOOT" -m venv venv
    if [[ $? -ne 0 ]]; then
        fail "could not create venv"
    fi
fi

VPY="$(pwd)/venv/bin/python"
if [[ ! -x "$VPY" ]]; then
    fail "venv python missing after create"
fi

# ----------------------------------------------------------------------
# Install dependencies
# ----------------------------------------------------------------------
echo "Installing kit + WorldEngine..."

if ! "$VPY" -m pip install --upgrade pip; then
    fail "pip upgrade"
fi

if ! "$VPY" -m pip install -r requirements.txt; then
    fail "pip install -r requirements.txt"
fi

if ! "$VPY" -m pip install -e "vendor/worldengine"; then
    fail "pip install -e vendor/worldengine"
fi

if ! "$VPY" -m pip install -e .; then
    fail "pip install -e ."
fi

if ! "$VPY" -m planetkit.cli init-config --preset balanced; then
    fail "init-config"
fi

if ! "$VPY" -m planetkit.cli write-params-doc; then
    fail "write-params-doc"
fi

# ----------------------------------------------------------------------
# Validate installation
# ----------------------------------------------------------------------
echo
echo "Validating install..."
if ! "$VPY" -m planetkit.doctor; then
    echo
    echo "Setup FAILED environment checks. Do not run PlanetKit yet."
    echo "Re-run setup.sh after fixing the errors above, or paste the report when asking for help."
    fail "planetkit.doctor failed"
fi

echo
echo "Setup complete. Run PlanetKit.sh (or your selected launcher)."
exit 0
