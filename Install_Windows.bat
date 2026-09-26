@echo off
title Chatty Chronos - Installer
color 0A

echo ========================================================
echo        Welcome to Chatty Chronos Installer
echo ========================================================
echo.
echo Checking for Python...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH!
    echo Please install Python 3.10 or newer from https://www.python.org/downloads/
    echo IMPORTANT: Make sure to check the box "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo Python found! Starting the deployment process...
echo.

python deploy.py

echo.
echo ========================================================
echo   If you saw no errors, the installation is complete!
echo   You can now double-click "Start_Chronos.bat" to play.
echo ========================================================
pause
