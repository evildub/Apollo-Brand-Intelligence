@echo off
REM ===================================================================
REM   Launch Apollo Brand Intelligence (Enterprise Edition)
REM ===================================================================
title Apollo Brand Intelligence Runner
cd /d "%~dp0"
echo Starting Apollo Brand Intelligence Enterprise Suite...
python run_apollo.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Apollo exited with code %ERRORLEVEL%
    pause
)
