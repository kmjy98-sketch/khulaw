# 홍형철 기본형법 — 미세조정 사전 백업 스크립트
# 작성: 2026-04-29
# 대상: 홍형철_기본형법/ 11개 .md (작은 폴더, 빠른 백업)
# 원칙: CLAUDE.md #1 (소스 보존), #15 (Verify-Before-Act), #16 (삭제 금지)
# 동작: Copy-Item으로 원본 보존하며 _백업/2026-04-29/ 하위에 .pre_normalize.md로 복사

param(
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 경로 설정
$SrcDir       = "H:\내 드라이브\sync\_교재원문\형법\홍형철_기본형법"
$Today        = "2026-04-29"
$BackupDir    = Join-Path $SrcDir "_백업\$Today"
$MetaDir      = "H:\내 드라이브\sync\_meta"
$ManifestPath = Join-Path $MetaDir "홍형철_백업_manifest_${Today}.json"

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " 홍형철 기본형법 — 미세조정 사전 백업" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " 소스  : $SrcDir"
Write-Host " 백업  : $BackupDir"
Write-Host " 모드  : $(if ($DryRun) { 'DRY-RUN (탐지만)' } else { 'APPLY (실제 복사)' })"
Write-Host " 일자  : $Today"
Write-Host ""

if (-not (Test-Path $SrcDir)) {
    Write-Host "! 소스 폴더 없음 — 중단" -ForegroundColor Red
    exit 1
}

# 백업 폴더 생성
if (-not $DryRun -and -not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    Write-Host "+ 백업 폴더 생성: $BackupDir" -ForegroundColor Green
}

# _백업 폴더 자체 제외
$Files = Get-ChildItem -Path $SrcDir -Filter "*.md" -File -Recurse -ErrorAction SilentlyContinue |
         Where-Object { $_.FullName -notmatch "\\_백업\\" -and $_.FullName -notmatch "\\_trash\\" }

$Total = $Files.Count
Write-Host "  - 발견: $Total 파일"
Write-Host ""

$Manifest = @{
    백업일자 = $Today
    백업시각 = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
    교재     = "홍형철_기본형법"
    모드     = $(if ($DryRun) { "dry-run" } else { "apply" })
    파일목록 = @()
    통계 = @{ 총파일수 = $Total; 성공 = 0; 실패 = 0; 스킵 = 0 }
}

$idx = 0
foreach ($F in $Files) {
    $idx++
    $RelPath  = $F.FullName.Substring($SrcDir.Length).TrimStart('\')
    $BaseName = [IO.Path]::GetFileNameWithoutExtension($F.Name)
    $NewName  = "${BaseName}.pre_normalize.md"
    $RelDir   = Split-Path $RelPath -Parent
    $DestDir  = if ($RelDir) { Join-Path $BackupDir $RelDir } else { $BackupDir }
    $DestPath = Join-Path $DestDir $NewName

    Write-Host "  [$idx/$Total] $($F.Name)" -ForegroundColor Gray

    $entry = @{
        원본       = $F.FullName
        백업       = $DestPath
        크기_바이트 = $F.Length
        수정시각   = $F.LastWriteTime.ToString("yyyy-MM-ddTHH:mm:ss")
    }

    try {
        if ($DryRun) {
            $entry.상태 = "dry-run"
            $Manifest.통계.스킵++
        } else {
            if (Test-Path $DestPath) {
                $entry.상태 = "이미존재—스킵"
                $Manifest.통계.스킵++
            } else {
                if (-not (Test-Path $DestDir)) {
                    New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
                }
                Copy-Item -Path $F.FullName -Destination $DestPath -Force
                $entry.상태 = "성공"
                $Manifest.통계.성공++
            }
        }
    } catch {
        $entry.상태 = "실패: $($_.Exception.Message)"
        $Manifest.통계.실패++
        Write-Host "    ! 실패: $($F.Name) — $($_.Exception.Message)" -ForegroundColor Red
    }

    $Manifest.파일목록 += $entry
}

# 매니페스트 저장
if (-not (Test-Path $MetaDir)) {
    New-Item -ItemType Directory -Path $MetaDir -Force | Out-Null
}
if (-not $DryRun) {
    $Manifest | ConvertTo-Json -Depth 10 | Out-File -FilePath $ManifestPath -Encoding utf8
    Write-Host ""
    Write-Host "+ 매니페스트 저장: $ManifestPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " 백업 결과 요약" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " 총파일수 : $($Manifest.통계.총파일수)"
Write-Host " 성공     : $($Manifest.통계.성공)" -ForegroundColor Green
Write-Host " 스킵     : $($Manifest.통계.스킵)" -ForegroundColor Yellow
Write-Host " 실패     : $($Manifest.통계.실패)" -ForegroundColor Red
Write-Host ""
if ($DryRun) {
    Write-Host " DRY-RUN 모드 — 실제 복사 없음. 실행하려면 -DryRun 옵션 제거." -ForegroundColor Yellow
} else {
    Write-Host " 백업 완료. 다음: python normalize_홍형철_미세조정.py --dry-run" -ForegroundColor Green
}
Write-Host ""
