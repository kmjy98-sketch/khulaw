@echo off
chcp 65001 > nul
cd /d "H:\내 드라이브"
python ".agent\backup\2026-04-29\apply_page_range_fix.py"
echo.
pause
