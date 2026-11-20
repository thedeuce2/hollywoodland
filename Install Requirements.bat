@echo off
cd /d "%~dp0"
echo Installing Hollywoodland dependencies (PySide6, Pillow)...
where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 -m pip install -r requirements.txt 2>nul || py -m pip install -r requirements.txt
) else (
    python -m pip install -r requirements.txt
)
echo.
echo Done! You can now double-click "Launch Hollywoodland.bat" to play.
pause
