@echo off
setlocal
cd /d "%~dp0"
where pythonw.exe >nul 2>&1
if errorlevel 1 (
  echo pythonw.exe introuvable. Installez Python 3.10+ ou lancez: python LevelUpDiag-MediKristal.pyw
  pause
  exit /b 1
)
start "LevelUpDiag-MediKristal" pythonw.exe "%~dp0LevelUpDiag-MediKristal.pyw"
