@rem FYERS auth utility launcher for Windows Task Scheduler
@rem Usage: run from project root, or set FYERS_PROJECT_ROOT below.

@echo off
setlocal

if not defined FYERS_PROJECT_ROOT (
    set "FYERS_PROJECT_ROOT=%~dp0..\.."
)

cd /d "%FYERS_PROJECT_ROOT%"

if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

python -m auth_helper.main >> logs\auth.log 2>&1
exit /b %ERRORLEVEL%
