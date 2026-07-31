@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Najpierw uruchom plik Instalacja.bat
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "app.py"
