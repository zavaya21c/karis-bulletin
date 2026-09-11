@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
if exist .venv\Scripts\python.exe goto run
py -3 -m venv .venv
if errorlevel 1 (
  echo Python 3.10 or newer is required. Install from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
:run
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe launch.py
:failed
pause
