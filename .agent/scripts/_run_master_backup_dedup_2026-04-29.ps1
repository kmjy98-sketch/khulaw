# Backup/Dedup Master Runner — 2026-04-29
# 사용자 요청: 4개 PowerShell 스크립트 일괄 실행
$ErrorActionPreference = "Continue"
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$LogPath = "H:\내 드라이브\_run_master_backup_dedup_2026-04-29.log"
$ScriptDir = "H:\내 드라이브\5.기타\scripts"

"=== START $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -FilePath $LogPath -Encoding utf8

function Run-Step {
    param([string]$Name, [string]$ScriptName, [string[]]$ScriptArgs)
    "" | Out-File -FilePath $LogPath -Append -Encoding utf8
    "### $Name ###" | Out-File -FilePath $LogPath -Append -Encoding utf8
    $ScriptPath = Join-Path $ScriptDir $ScriptName
    "CMD: $ScriptPath $($ScriptArgs -join ' ')" | Out-File -FilePath $LogPath -Append -Encoding utf8
    if (-not (Test-Path -LiteralPath $ScriptPath)) {
        "ERROR: Script not found: $ScriptPath" | Out-File -FilePath $LogPath -Append -Encoding utf8
        return
    }
    try {
        $output = & powershell -ExecutionPolicy Bypass -File $ScriptPath @ScriptArgs 2>&1 | Out-String
        $output | Out-File -FilePath $LogPath -Append -Encoding utf8
        "EXIT: $LASTEXITCODE" | Out-File -FilePath $LogPath -Append -Encoding utf8
    } catch {
        "EXCEPTION: $_" | Out-File -FilePath $LogPath -Append -Encoding utf8
    }
}

Run-Step -Name "Backup 송영곤" -ScriptName "backup_송영곤_2026-04-29.ps1" -ScriptArgs @("-Target","본책")
Run-Step -Name "Backup 김기용" -ScriptName "backup_김기용_2026-04-29.ps1" -ScriptArgs @("-Target","전체")
Run-Step -Name "Backup 홍형철" -ScriptName "backup_홍형철_2026-04-29.ps1" -ScriptArgs @()
Run-Step -Name "Dedup 송영곤 (DryRun)" -ScriptName "dedup_chunk_2026-04-29.ps1" -ScriptArgs @("-Target","송영곤","-DryRun")

"" | Out-File -FilePath $LogPath -Append -Encoding utf8
"=== END $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -FilePath $LogPath -Append -Encoding utf8
