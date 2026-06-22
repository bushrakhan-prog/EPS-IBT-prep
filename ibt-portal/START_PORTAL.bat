@echo off
title IBT Portal
color 0A

echo.
echo  ================================================
echo   IBT Prep Portal - Starting...
echo  ================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python is not installed!
    echo.
    echo  Please install Python from:
    echo  https://www.python.org/downloads/
    echo.
    echo  Make sure to check "Add Python to PATH"
    echo  during installation.
    echo.
    pause
    exit
)

:: Go to the folder where this bat file is located
cd /d "%~dp0"

:: Install packages if not already installed
echo  Checking required packages...
pip install flask flask-sqlalchemy werkzeug >nul 2>&1
echo  Packages ready.
echo.

:: Open browser after 2 seconds
echo  Opening browser at http://localhost:5000 ...
start "" /b cmd /c "timeout /t 2 >nul && start http://localhost:5000"

echo  ================================================
echo   Portal is running!
echo   Open: http://localhost:5000
echo.
echo   Admin login   : admin / admin123
echo   Keep this window open while using the portal.
echo   To stop: close this window.
echo  ================================================
echo.

:: Start Flask server
python app.py

pause
