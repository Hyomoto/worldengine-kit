@echo off
setlocal
cd /d "%~dp0.."

if not exist "venv\Scripts\python.exe" (
  echo Run setup.bat first.
  exit /b 1
)

echo Installing PyInstaller...
.\venv\Scripts\python.exe -m pip install "pyinstaller>=6.0"

echo Building onedir...
.\venv\Scripts\python.exe -m PyInstaller --noconfirm PlanetKit.spec
if errorlevel 1 exit /b 1

echo.
echo Output: dist\WorldEnginePlanetKit\
echo Zip that folder for distribution.
endlocal
