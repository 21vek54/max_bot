@echo off
cd /d "%~dp0"

REM Stop previous bot.py processes to avoid stale lock conflicts
powershell -NoProfile -Command "Get-CimInstance Win32_Process ^| Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'bot.py' } ^| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>nul

if exist .bot.lock del /f /q .bot.lock >nul 2>nul

if not exist .venv\Scripts\python.exe (
  echo [ERROR] Python in .venv not found: .venv\Scripts\python.exe
  pause
  exit /b 1
)

.\.venv\Scripts\python.exe -u bot.py

echo.
echo Bot stopped. Press any key to close...
pause >nul
