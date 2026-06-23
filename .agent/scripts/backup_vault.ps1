<#
.SYNOPSIS
  E:\법학볼트(정본) 단방향 백업 러너 — rclone copy(클라우드) 또는 robocopy(외장/로컬).
  비삭제(copy만, /MIR·sync 금지) · 비밀제외 · 재생성물제외 · VAULT_ROOT 자동해석 · 로그.

.DESCRIPTION
  설계: sync/_meta/E백업체계_2026-06-23.md
  원칙(#16): 정본에서 지운 파일이 백업에서 자동삭제되면 안 된다 → 절대 /MIR / sync --delete 미사용.
  기본은 DryRun(목록만). 실제 실행은 -Execute 명시.

.PARAMETER Target
  'rclone'(클라우드, OAuth 선행) 또는 'robocopy'(외장 HDD/로컬 폴더).

.PARAMETER RcloneRemote
  rclone 대상 remote:path. 예 'gdrive:법학볼트_백업'. (rclone config로 사전 구성)

.PARAMETER Dest
  robocopy 대상 폴더. 예 'F:\법학볼트_백업'.

.PARAMETER Execute
  지정 시 실제 복사. 미지정 시 DryRun(robocopy /L · rclone --dry-run).

.EXAMPLE
  # 클라우드 dry-run → 검토 → 실행
  .\backup_vault.ps1 -Target rclone -RcloneRemote "gdrive:법학볼트_백업"
  .\backup_vault.ps1 -Target rclone -RcloneRemote "gdrive:법학볼트_백업" -Execute

.EXAMPLE
  # 외장 HDD
  .\backup_vault.ps1 -Target robocopy -Dest "F:\법학볼트_백업" -Execute
#>
[CmdletBinding()]
param(
  [ValidateSet('rclone','robocopy')] [string]$Target = 'rclone',
  [string]$RcloneRemote = 'gdrive:법학볼트_백업',
  [string]$Dest = '',
  [switch]$Execute
)

$ErrorActionPreference = 'Stop'

# --- 소스 = VAULT_ROOT (vault.json 단일 소스, 디커플) ---
$cfgPath = Join-Path $PSScriptRoot '..\config\vault.json'
if (-not (Test-Path -LiteralPath $cfgPath)) { throw "vault.json 없음: $cfgPath" }
$Src = (Get-Content -Raw -LiteralPath $cfgPath -Encoding UTF8 | ConvertFrom-Json).vault_root
if (-not (Test-Path -LiteralPath $Src)) { throw "VAULT_ROOT 경로 없음: $Src" }

$date   = Get-Date -Format 'yyyy-MM-dd'
$logDir = Join-Path $Src '.agent\state\backup_logs'
if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
$log    = Join-Path $logDir "backup_${Target}_${date}.log"

# --- 제외 규칙 (E백업체계 §3) ---
$exclDirNames = @('.git','node_modules','__pycache__','_trash','.obsidian')      # 이름 일치(어디서나)
$exclDirPaths = @('.agent\temp_toc','.agent\temp_pdf_extract')                   # 특정 경로
$exclFiles    = @('.env','.env.*','*.key','*.pem','*.p12','.mcp.json','mcp.json','credentials*','token*')

$mode = if ($Execute) { 'EXECUTE(실복사)' } else { 'DRY-RUN(목록만)' }
Write-Host "===== 법학볼트 백업 [$Target] $mode =====" -ForegroundColor Cyan
Write-Host "SRC : $Src"
Write-Host "LOG : $log"
Write-Host "안전: 단방향 copy · /MIR 미사용(삭제 전파 차단, #16) · 비밀/.git/node_modules 제외" -ForegroundColor Yellow

if ($Target -eq 'robocopy') {
  if (-not $Dest) { throw "-Dest 필요 (예: F:\법학볼트_백업)" }
  Write-Host "DEST: $Dest"
  $rcArgs = @($Src, $Dest, '/E','/COPY:DAT','/DCOPY:DAT','/XO','/R:1','/W:1','/XJ','/NP','/TEE',"/LOG+:$log")
  if (-not $Execute) { $rcArgs += '/L' }            # 목록만(복사 안 함)
  $rcArgs += '/XD'; $rcArgs += $exclDirNames
  foreach ($p in $exclDirPaths) { $rcArgs += (Join-Path $Src $p) }
  $rcArgs += '/XF'; $rcArgs += $exclFiles
  # NOTE: /MIR 는 의도적으로 절대 추가하지 않는다 (삭제 전파 금지).
  & robocopy @rcArgs
  $code = $LASTEXITCODE
  # robocopy 종료코드: 0~7=정상(8+ 오류). 비트0=복사,1=추가,2=불일치,3=실패,4=불일치+,...
  if ($code -ge 8) { Write-Host "robocopy 오류 (exit=$code) — 로그 확인" -ForegroundColor Red; exit $code }
  Write-Host "robocopy 완료 (exit=$code, 정상범위)" -ForegroundColor Green
}
elseif ($Target -eq 'rclone') {
  if (-not (Get-Command rclone -ErrorAction SilentlyContinue)) {
    throw "rclone 미설치. 'winget install Rclone.Rclone' 후 'rclone config'로 '$RcloneRemote' 구성."
  }
  Write-Host "DEST: $RcloneRemote"
  $ex = @()
  foreach ($n in $exclDirNames) { $ex += @('--exclude', "$n/**"); $ex += @('--exclude', "**/$n/**") }
  foreach ($p in $exclDirPaths) { $ex += @('--exclude', (($p -replace '\\','/') + '/**')) }
  foreach ($f in $exclFiles)    { $ex += @('--exclude', $f) }
  $rcArgs = @('copy', $Src, $RcloneRemote,
              '--transfers','4','--checkers','8','--progress',
              '--log-file', $log, '--log-level','INFO') + $ex
  if (-not $Execute) { $rcArgs += '--dry-run' }     # copy(=비삭제). sync 미사용
  & rclone @rcArgs
  $code = $LASTEXITCODE
  if ($code -ne 0) { Write-Host "rclone 오류 (exit=$code) — 로그 확인" -ForegroundColor Red; exit $code }
  Write-Host "rclone 완료 (exit=0)" -ForegroundColor Green
}

if (-not $Execute) {
  Write-Host "`n[DRY-RUN] 실제 백업은 동일 명령에 -Execute 추가." -ForegroundColor Yellow
} else {
  Write-Host "`n검증 권장: python .agent\scripts\backup_inventory.py 재생성 후 대상과 파일수·용량 대조." -ForegroundColor Cyan
}
# robocopy 0~7 / rclone 0 = 성공 → 스케줄러 오인 방지 위해 0으로 정규화
exit 0
