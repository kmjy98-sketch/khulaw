@echo off
rem 진도보드 v2 — 더블클릭 한 번으로 서버 기동(이미 떠 있으면 재사용) + 브라우저 열기
set PYW=C:\Users\111\AppData\Local\Programs\Python\Python313\pythonw.exe
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://localhost:8770/' -TimeoutSec 2 -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
    start "" "%PYW%" "%~dp0board_server_v2.py" --no-browser
    timeout /t 3 /nobreak >nul
)
start "" http://localhost:8770/
