@echo off
chcp 65001 > nul
powershell.exe -ExecutionPolicy Bypass -File "%~dp0_run_master_backup_dedup_2026-04-29.ps1"
echo.
echo === 실행 완료 — 로그: %~dp0_run_master_backup_dedup_2026-04-29.log ===
pause
