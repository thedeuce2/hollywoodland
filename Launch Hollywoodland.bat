@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 main.py %* 2>nul || py main.py %*
) else (
    python main.py %*
)
if errorlevel 1 (
    echo.
    echo Failed to launch Hollywoodland. If this is your first time running it,
    echo double-click "Install Requirements.bat" first (Python 3.11+ required).
    pause
)
