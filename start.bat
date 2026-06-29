@echo off
echo Starting 2026 World Cup Simulator...

REM Start the python server in the background of the current window
start /b python server.py

REM Give the server a moment to start up
timeout /t 2 /nobreak >nul

REM Open the application in the default web browser
start http://localhost:8000

echo Application launched! 
echo This console window is now running the backend server.
echo Simply close this window to shut down the application when you are done.
pause
