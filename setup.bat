@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYBOOT="
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYBOOT=py -3"
)
if not defined PYBOOT (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Python was not found on PATH.
    echo Install Python 3.9+ from https://www.python.org/downloads/
    echo Enable "Add python.exe to PATH", then re-run setup.bat.
    goto :fail
  )
  python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
  if errorlevel 1 (
    echo Python 3.9+ is required.
    goto :fail
  )
  set "PYBOOT=python"
)

echo Using bootstrap interpreter: %PYBOOT%

if not exist "vendor\worldengine\pyproject.toml" (
  echo vendor\worldengine missing. If you are a maintainer, run:
  echo   python scripts\sync_from_dev.py
  goto :fail
)

if not exist "venv\Scripts\python.exe" (
  echo Creating venv...
  %PYBOOT% -m venv venv
  if errorlevel 1 (
    echo FAILED: could not create venv.
    goto :fail
  )
)

set "VPY=.\venv\Scripts\python.exe"
if not exist "%VPY%" (
  echo FAILED: venv python missing after create.
  goto :fail
)

echo Installing kit + WorldEngine...
"%VPY%" -m pip install --upgrade pip
if errorlevel 1 (
  echo FAILED: pip upgrade.
  goto :fail
)

"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo FAILED: pip install -r requirements.txt
  goto :fail
)

"%VPY%" -m pip install -e ".\vendor\worldengine"
if errorlevel 1 (
  echo FAILED: pip install -e vendor\worldengine
  goto :fail
)

"%VPY%" -m pip install -e .
if errorlevel 1 (
  echo FAILED: pip install -e .
  goto :fail
)

"%VPY%" -m planetkit.cli init-config --preset balanced
if errorlevel 1 (
  echo FAILED: init-config
  goto :fail
)

"%VPY%" -m planetkit.cli write-params-doc
if errorlevel 1 (
  echo FAILED: write-params-doc
  goto :fail
)

echo.
echo Validating install...
"%VPY%" -m planetkit.doctor
if errorlevel 1 (
  echo.
  echo Setup FAILED environment checks. Do not run PlanetKit yet.
  echo Re-run setup.bat after fixing the errors above, or paste the report when asking for help.
  goto :fail
)

echo.
echo Setup complete. Run PlanetKit.bat
endlocal
exit /b 0

:fail
echo.
pause
endlocal
exit /b 1
