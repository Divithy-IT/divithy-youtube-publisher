@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Nie znaleziono Pythona. Zainstaluj Python 3.11 lub nowszy z python.org.
  pause
  exit /b 1
)
py -3 -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.
echo Instalacja zakonczona. Uruchom teraz Uruchom_publikator.bat
pause
