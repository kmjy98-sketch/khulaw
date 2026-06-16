@echo off
chcp 65001 > nul
powershell.exe -ExecutionPolicy Bypass -File "%~dp0_run_master_2026-04-29.ps1"
