@echo off
rem === Stop the Jindo board server (foreground or background). ===
powershell -NoProfile -Command "$p=Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Where-Object { $_.CommandLine -like '*board_server*' }; if($p){ $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('stopped PID ' + $_.ProcessId) } } else { Write-Host 'no running board server.' }"
echo.
echo done. press any key to close.
pause >nul
