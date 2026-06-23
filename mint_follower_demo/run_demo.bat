@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
python app.py
pause
