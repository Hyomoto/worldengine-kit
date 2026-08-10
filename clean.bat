@echo off
setlocal
cd /d "%~dp0.."
python scripts\clean_kit.py %*
endlocal
