#!/usr/bin/env bash

# Converted from Windows batch script to Bash
# Preserves original behavior for PlanetKit setup and execution.

# Switch to the directory where this script resides
cd "$(dirname "$0")" || exit 1

# Check whether the virtual environment Python exists
if [ ! -f "./venv/bin/python" ]; then
    echo "venv missing. Run setup.bat first and wait until it says Setup complete."
    # Pause for user input (equivalent to batch 'pause')
    read -n 1 -s -r -p "Press any key to continue . . ."
    echo
    exit 1
fi

echo "Checking environment..."
./venv/bin/python -m planetkit.doctor

# If doctor fails, report and exit
if [ $? -ne 0 ]; then
    echo
    echo "PlanetKit will not start until setup succeeds."
    echo "Re-run setup.bat, then try again. Copy the report above if you need help."
    read -n 1 -s -r -p "Press any key to continue . . ."
    echo
    exit 1
fi

# Environment OK
export PLANETKIT_DOCTOR_OK=1

# Run PlanetKit CLI with all passed arguments
./venv/bin/python -m planetkit.cli "$@"
EC=$?

# If CLI exited non‑zero, show message and pause
if [ "$EC" -ne 0 ]; then
    echo
    echo "PlanetKit exited with code $EC."
    read -n 1 -s -r -p "Press any key to continue . . ."
    echo
fi

# Exit with the captured exit code
exit $EC
