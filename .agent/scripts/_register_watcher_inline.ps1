# Gemini Watcher 인라인 등록 스크립트
# 사용법: powershell -ExecutionPolicy Bypass -File "H:\내 드라이브\.agent\scripts\_register_watcher_inline.ps1"
# (인자 -ExecutionPolicy Bypass 가 있으면 디지털 서명 없어도 실행됨)

$ErrorActionPreference = "Stop"
$TaskName = "GeminiOpsWatcher"
$WatcherScript = "H:\내 드라이브\.agent\scripts\_gemini_watcher.py"

# 1. Python 실행 파일 결정
$pw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
$p  = (Get-Command python.exe  -ErrorAction SilentlyContinue).Source
if ($pw) {
    $exec = $pw
    $hidden = $false
    Write-Host "사용: pythonw.exe ($pw)" -ForegroundColor Green
} elseif ($p) {
    $exec = $p
    $hidden = $true
    Write-Host "사용: python.exe + Hidden ($p)" -ForegroundColor Green
} else {
    Write-Error "Python이 PATH에 없습니다."
    exit 1
}

# 2. 스크립트 존재 확인
if (-not (Test-Path $WatcherScript)) {
    Write-Error "Watcher 스크립트 없음: $WatcherScript"
    exit 1
}

# 3. 기존 Task 제거
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "기존 Task 제거" -ForegroundColor Yellow
}

# 4. Task 구성
$Action = New-ScheduledTaskAction -Execute $exec -Argument "`"$WatcherScript`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settingsArgs = @{
    AllowStartIfOnBatteries    = $true
    DontStopIfGoingOnBatteries = $true
    StartWhenAvailable         = $true
    RestartCount               = 999
    RestartInterval            = (New-TimeSpan -Minutes 1)
    ExecutionTimeLimit         = (New-TimeSpan -Seconds 0)
}
if ($hidden) { $settingsArgs['Hidden'] = $true }
$Settings  = New-ScheduledTaskSettingsSet @settingsArgs
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

# 5. 등록
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Gemini Op 로그 watcher" | Out-Null
Write-Host "Task 등록 완료: $TaskName" -ForegroundColor Green

# 6. 즉시 시작
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 4

# 7. 검증
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host ""
Write-Host "=== 검증 ===" -ForegroundColor Cyan
Write-Host "  마지막 실행: $($info.LastRunTime)"
Write-Host "  결과 코드:   $($info.LastTaskResult)  (0 또는 267009=실행중 이면 정상)"

$logPath = "H:\내 드라이브\.auto-memory\gemini_ops\_watcher.log"
if (Test-Path $logPath) {
    Write-Host ""
    Write-Host "=== watcher.log 최근 3줄 ===" -ForegroundColor Cyan
    Get-Content $logPath -Tail 3
} else {
    Write-Host "watcher.log 아직 생성 안 됨. 10초 후 다시 확인:" -ForegroundColor Yellow
    Write-Host "  Get-Content `"$logPath`" -Tail 3"
}
