@echo off
chcp 65001 >nul
cd /d "%~dp0"
:loop
echo ==========================================
echo   PredSmesh bot - starting
echo   Keep Happ/Xray proxy running!
echo   Stop: Ctrl+C or close this window
echo ==========================================
echo.
".venv\Scripts\python.exe" -m app.bot
echo.
echo Bot stopped. Exit code: %ERRORLEVEL%
echo Restarting in 5 seconds... Press Ctrl+C to stop.
timeout /t 5 /nobreak >nul
goto loop
