# Gemini Op Watcher 작업 스케줄러 등록 스크립트
#
# 사용법 (PowerShell 관리자 권한 불필요, 사용자 권한으로 충분):
#   .\_register_watcher_task.ps1               # 등록
#   .\_register_watcher_task.ps1 -Uninstall    # 해제
#   .\_register_watcher_task.ps1 -Status       # 현재 상태 확인
#
# 동작:
#   - 트리거: 사용자 로그인 시
#   - 명령: pythonw.exe (콘솔 창 없음)
#   - 실패 시 1분 후 재시작, 무한 재시도
#   - 절전 모드에서도 실행

param(
    [switch]$Uninstall,
    [switch]$Status
)

$TaskName = "GeminiOpsWatcher"
$WatcherScript = "H:\내 드라이브\.agent\scripts\_gemini_watcher.py"

# pythonw.exe 경로 자동 탐색
$PythonW = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonW) {
    # python.exe 기준으로 pythonw.exe 추정
    $Python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if ($Python) {
        $PythonW = $Python -replace 'python\.exe$', 'pythonw.exe'
    }
}

if ($Status) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        Write-Host "Task '$TaskName' 등록됨"
        $info = Get-ScheduledTaskInfo -TaskName $TaskName
        Write-Host "  마지막 실행: $($info.LastRunTime)"
        Write-Host "  마지막 결과: $($info.LastTaskResult)"
        Write-Host "  다음 실행: $($info.NextRunTime)"
        Write-Host "  상태: $($task.State)"
    } else {
        Write-Host "Task '$TaskName' 등록되지 않음"
    }
    exit 0
}

if ($Uninstall) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Task '$TaskName' 해제 완료"
    } else {
        Write-Host "Task '$TaskName' 등록되어 있지 않음"
    }
    exit 0
}

# 사전 점검
if (-not $PythonW) {
    Write-Error "pythonw.exe 경로를 찾을 수 없습니다. Python이 PATH에 등록되어 있는지 확인하세요."
    exit 1
}
if (-not (Test-Path $WatcherScript)) {
    Write-Error "Watcher 스크립트가 없습니다: $WatcherScript"
    exit 1
}

# 기존 task가 있으면 제거 후 재등록
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "기존 task 제거"
}

# Action: pythonw.exe로 watcher 스크립트 실행
$Action = New-ScheduledTaskAction `
    -Execute $PythonW `
    -Argument "`"$WatcherScript`""

# Trigger: 사용자 로그인 시
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Settings: 실패 시 재시도, 절전 모드에서도 실행, 시간 제한 없음
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0)

# Principal: 현재 사용자 계정, 일반 권한
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

# 등록
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Gemini Op 로그 감시 watcher (3초 폴링, .auto-memory/gemini_ops/)" | Out-Null

Write-Host "Task '$TaskName' 등록 완료"
Write-Host "  실행 파일: $PythonW"
Write-Host "  스크립트: $WatcherScript"
Write-Host "  트리거: 사용자 로그인 시"
Write-Host ""
Write-Host "지금 바로 시작하려면:"
Write-Host "  Start-ScheduledTask -TaskName $TaskName"
