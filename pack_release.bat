@echo off
setlocal
cd /d "%~dp0.."
python scripts\clean_kit.py --deep-vendor
if errorlevel 1 exit /b 1
python scripts\pack_release.py %*
endlocal
