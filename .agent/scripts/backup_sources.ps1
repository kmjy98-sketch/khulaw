<#
.SYNOPSIS
  선별 다중소스 백업 — E:\법학볼트(필수) + C:대화기록 + 이주로그 + (선택)LiquidText.
  rclone copy(비삭제·/MIR금지) · 비밀/캐시/시스템 제외 · DryRun 기본.

.DESCRIPTION
  설계: sync/_meta/E백업체계_2026-06-23.md
  "E: 전체" 백업이 캐시중복 오류를 낸 이유 = 245GB content_cache·17GB 앱데이터·시스템 폴더까지 긁어서.
  → 본 스크립트는 '실데이터'만 소스로 선별한다. 245GB content_cache는 제외(재생성 앱캐시).
  원칙(#16): copy만(절대 sync/--delete 미사용).

.PARAMETER RcloneRemote
  rclone remote 루트. 예 'gdrive:법학볼트_백업'. (rclone config로 사전 구성)

.PARAMETER IncludeChatLogs
  C:\Users\111\.claude\projects(대화기록 1.1GB) 포함. 기본 포함 권장.

.PARAMETER IncludeLiquidText
  E:\LocalState(LiquidText 주석·프로젝트 17GB) 포함. ★실행 전 LiquidText 앱 종료 필수(라이브 DB).

.PARAMETER Execute
  지정 시 실복사. 미지정 시 DryRun(rclone --dry-run).

.EXAMPLE
  # 권장: 볼트+대화기록 dry-run → 검토 → 실행
  .\backup_sources.ps1 -RcloneRemote "gdrive:법학볼트_백업" -IncludeChatLogs
  .\backup_sources.ps1 -RcloneRemote "gdrive:법학볼트_백업" -IncludeChatLogs -Execute

.EXAMPLE
  # LiquidText 주석까지(앱 종료 후)
  .\backup_sources.ps1 -RcloneRemote "gdrive:법학볼트_백업" -IncludeChatLogs -IncludeLiquidText -Execute
#>
[CmdletBinding()]
param(
  [string]$RcloneRemote = 'gdrive:법학볼트_백업',
  [switch]$IncludeChatLogs,
  [switch]$IncludeLiquidText,
  [switch]$IncludeConfig,
  [switch]$Execute
)
$ErrorActionPreference = 'Stop'

# --- 볼트 루트(vault.json 디커플) ---
$cfgPath = Join-Path $PSScriptRoot '..\config\vault.json'
$VaultRoot = (Get-Content -Raw -LiteralPath $cfgPath -Encoding UTF8 | ConvertFrom-Json).vault_root

$date   = Get-Date -Format 'yyyy-MM-dd'
$logDir = Join-Path $VaultRoot '.agent\state\backup_logs'
if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

# --- 공통 제외 ---
$exclDirNames = @('.git','node_modules','__pycache__','_trash','.obsidian','content_cache')
$exclFiles    = @('.env','.env.*','*.key','*.pem','*.p12','.mcp.json','mcp.json','credentials*','token*')

# --- 소스 정의 ---
$sources = @()
$sources += @{ Name='법학볼트'; Src=$VaultRoot; Dest='법학볼트'; Extra=@() }
$logFile = Join-Path 'E:\' '_이주로그_2026-06-22.txt'
if (Test-Path -LiteralPath $logFile) { $sources += @{ Name='이주로그'; Src=$logFile; Dest='_misc'; Extra=@(); IsFile=$true } }
if ($IncludeChatLogs) {
  $sources += @{ Name='대화기록(C:)'; Src='C:\Users\111\.claude\projects'; Dest='claude_대화기록'; Extra=@() }
}
if ($IncludeLiquidText) {
  Write-Host "[경고] LiquidText 앱을 종료했는지 확인하라(라이브 DB 복사는 손상 위험)." -ForegroundColor Red
  $sources += @{ Name='LiquidText'; Src='E:\LocalState'; Dest='LiquidText_LocalState'; Extra=@('*.log','*-journal','MetroLogs/**','LTSyncErrors/**','Lucene/**') }
}

if ($IncludeConfig) {
  # 전역 Claude 설정(볼트 밖): CLAUDE.md·settings.json·scheduled-tasks 등. projects(대화기록·메모리)는 -IncludeChatLogs로 별도. 비밀·캐시·재생성 제외.
  $sources += @{ Name='Claude설정(C:)'; Src='C:\Users\111\.claude'; Dest='claude_config';
                 Extra=@('projects/**','tmp/**','cache/**','telemetry/**','shell-snapshots/**','debug/**','sessions/**','session-env/**','tasks/**','ide/**','downloads/**','plugins/**','.credentials.json') }
}

if (-not (Get-Command rclone -ErrorAction SilentlyContinue)) {
  throw "rclone 미설치. 'winget install Rclone.Rclone' 후 'rclone config'로 '$RcloneRemote' 구성."
}

$mode = if ($Execute) { 'EXECUTE(실복사)' } else { 'DRY-RUN(목록만)' }
Write-Host "===== 선별 다중소스 백업 [$mode] =====" -ForegroundColor Cyan
Write-Host "REMOTE: $RcloneRemote" -ForegroundColor Cyan
Write-Host "안전: copy(비삭제)·/MIR금지 · content_cache/비밀/.git/node_modules 제외" -ForegroundColor Yellow
Write-Host ("소스 {0}개: {1}" -f $sources.Count, (($sources | ForEach-Object { $_.Name }) -join ', '))

$fail = 0
foreach ($s in $sources) {
  if (-not (Test-Path -LiteralPath $s.Src)) { Write-Host "[건너뜀] 소스 없음: $($s.Src)" -ForegroundColor DarkYellow; continue }
  $dst = "$RcloneRemote/$($s.Dest)"
  $log = Join-Path $logDir ("backup_{0}_{1}.log" -f ($s.Dest -replace '[^\w가-힣]','_'), $date)
  Write-Host "`n--- [$($s.Name)]  $($s.Src)  ->  $dst ---" -ForegroundColor Green
  $ex = @()
  foreach ($n in $exclDirNames) { $ex += @('--exclude', "$n/**"); $ex += @('--exclude', "**/$n/**") }
  foreach ($f in $exclFiles)    { $ex += @('--exclude', $f) }
  foreach ($f in $s.Extra)      { $ex += @('--exclude', $f) }
  $rcArgs = @('copy', $s.Src, $dst, '--transfers','4','--checkers','8','--progress',
              '--log-file', $log, '--log-level','INFO') + $ex
  if (-not $Execute) { $rcArgs += '--dry-run' }
  & rclone @rcArgs
  if ($LASTEXITCODE -ne 0) { Write-Host "  [오류] rclone exit=$LASTEXITCODE — $log 확인" -ForegroundColor Red; $fail++ }
  else { Write-Host "  [완료] $($s.Name)" -ForegroundColor Green }
}

Write-Host ""
if ($fail -gt 0) { Write-Host "$fail개 소스 오류 — 로그 확인" -ForegroundColor Red; exit 1 }
if (-not $Execute) { Write-Host "[DRY-RUN] 실제 백업은 -Execute 추가." -ForegroundColor Yellow }
else { Write-Host "완료. 검증: rclone check 또는 remote 용량 대조." -ForegroundColor Cyan }
exit 0
