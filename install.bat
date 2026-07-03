@echo off
setlocal

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    python -m venv venv
)

set "PY=venv\Scripts\python.exe"

"%PY%" -m ensurepip --upgrade >nul 2>&1
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r requirements.txt
"%PY%" -m pip install -r requirements-fyers.txt --no-deps
"%PY%" -m playwright install msedge

echo.
echo Dependencies installed for Python 3.13.
exit /b 0
