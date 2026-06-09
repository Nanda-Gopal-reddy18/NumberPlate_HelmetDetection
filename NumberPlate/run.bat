@echo off
setlocal

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "VENV=%ROOT%\nh"
set "PY=%VENV%\Scripts\python.exe"

"%PY%" "%~dp0Main.py"
pause
