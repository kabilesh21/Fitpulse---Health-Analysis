@echo off
title FitPulse - Health Anomaly Detection System
echo ========================================================
echo       FitPulse Health Anomaly Detection System
echo ========================================================
echo.

rem Check if virtual environment exists inside backend
if exist backend\venv goto :venv_exists

echo [1/3] Creating Python virtual environment (venv) in backend...
python -m venv backend\venv
if %errorlevel% neq 0 goto :venv_error
goto :venv_created

:venv_exists
echo [1/3] Python virtual environment (venv) already exists.
goto :venv_done

:venv_created
echo Virtual environment created successfully.

:venv_done
rem Activate virtual environment
echo.
echo [2/3] Activating virtual environment and installing dependencies...
call backend\venv\Scripts\activate

rem Install requirements
pip install -r backend\requirements.txt
if %errorlevel% neq 0 goto :pip_error

echo.
echo [3/3] Launching FitPulse Web Application...
echo.
echo If the browser does not open automatically,
echo please navigate to http://127.0.0.1:5000 manually.
echo.
echo Press Ctrl+C in this terminal to stop the server.
echo.

start http://127.0.0.1:5000
cd backend
python app.py
goto :eof

:venv_error
echo.
echo ERROR: Failed to create virtual environment.
echo Ensure Python is installed and in your PATH.
pause
exit /b 1

:pip_error
echo.
echo ERROR: Failed to install dependencies.
pause
exit /b 1
