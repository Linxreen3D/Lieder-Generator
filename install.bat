@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo === Lieder-Generator: Installation ===

set "PY="
where py >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  where python >nul 2>nul
  if not errorlevel 1 set "PY=python"
)
if not defined PY goto nopython
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto nopython

if not exist ".venv\Scripts\python.exe" (
  echo Erstelle virtuelle Umgebung .venv ...
  %PY% -m venv .venv
  if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
".venv\Scripts\python.exe" -m pip install -e ".[ai]" -q
if errorlevel 1 goto fail

if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo Fertig! Optional: API-Key in die Datei .env eintragen.
echo Starten mit Doppelklick auf start.bat
if not "%~1"=="nopause" pause
exit /b 0

:nopython
echo.
echo Python 3.10 oder neuer wurde nicht gefunden.
echo Installiere Python von https://www.python.org/downloads/
echo WICHTIG: beim Installieren "Add python.exe to PATH" anhaken.
echo Alternativ in PowerShell:  winget install Python.Python.3.12
pause
exit /b 1

:fail
echo.
echo Installation fehlgeschlagen - siehe Meldungen oben.
pause
exit /b 1
