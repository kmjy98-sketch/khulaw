@echo off
rem === Jindo board server in BACKGROUND (no console window). ===
rem === To stop it later, run the stop bat in this folder. ===
cd /d "%~dp0"
set "PYW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw.exe"
start "" "%PYW%" board_server_v2.py
