@echo off
setlocal
if "%~1"=="" (
  echo usage: %~nx0 C:\path\to\MediKristal [baseline^|software^|delivery^|release^|deep]
  exit /b 64
)
set CAMPAIGN=%~2
if "%CAMPAIGN%"=="" set CAMPAIGN=release
python "%~dp0levelupdiag.py" --target "%~1" run "%CAMPAIGN%"
exit /b %ERRORLEVEL%
