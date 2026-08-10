@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
  echo venv missing. Run setup.bat first and wait until it says Setup complete.
  pause
  exit /b 1
)

echo Checking environment...
.\venv\Scripts\python.exe -m planetkit.doctor
if errorlevel 1 (
  echo.
  echo PlanetKit will not start until setup succeeds.
  echo Re-run setup.bat, then try again. Copy the report above if you need help.
  pause
  exit /b 1
)

set "PLANETKIT_DOCTOR_OK=1"
.\venv\Scripts\python.exe -m planetkit.cli %*
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo PlanetKit exited with code %EC%.
  pause
)
endlocal
exit /b %EC%
