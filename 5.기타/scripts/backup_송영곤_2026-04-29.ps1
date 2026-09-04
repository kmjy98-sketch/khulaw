# 송영곤 200+ 정규화 사전 백업 스크립트
# 작성: 2026-04-29
# 대상: 송영곤_논점민법_본책/ + 송영곤_논점민법_보충/ 모든 .md
# 원칙: CLAUDE.md #1 (소스 보존), #15 (Verify-Before-Act), #16 (삭제 금지)
# 동작: Copy-Item으로 원본 보존하며 _백업/2026-04-29/ 하위에 복사

param(
    [switch]$DryRun = $false,
    [ValidateSet("본책", "보충", "전체")]
    [string]$Target = "전체"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 경로 설정
$BaseRoot = "H:\내 드라이브\sync\_교재원문\민법"
$BonChaek  = Join-Path $BaseRoot "송영곤_논점민법_본책"
$BoChung   = Join-Path $BaseRoot "송영곤_논점민법_보충"
$Today     = "2026-04-29"
$MetaDir   = "H:\내 드라이브\sync\_meta"
$ManifestPath = Join-Path $MetaDir "송영곤_백업_manifest_${Today}.json"

# 백업 대상 폴더 결정
$Targets = @()
if ($Target -eq "본책" -or $Target -eq "전체") {
    $Targets += @{Name="본책"; SrcDir=$BonChaek; BackupDir=(Join-Path $BonChaek "_백업\$Today")}
}
if ($Target -eq "보충" -or $Target -eq "전체") {
    $Targets += @{Name="보충"; SrcDir=$BoChung; BackupDir=(Join-Path $BoChung "_백업\$Today")}
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " 송영곤 200+ 정규화 사전 백업 스크립트" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " 대상  : $Target"
Write-Host " 모드  : $(if ($DryRun) { 'DRY-RUN (탐지만)' } else { 'APPLY (실제 복사)' })"
Write-Host " 일자  : $Today"
Write-Host ""

$AllManifest = @{
    백업일자 = $Today
    백업시각 = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
    대상 = $Target
    모드 = $(if ($DryRun) { "dry-run" } else { "apply" })
    파일목록 = @()
    통계 = @{
        총파일수 = 0
        성공 = 0
        실패 = 0
        스킵 = 0
    }
}

foreach ($T in $Targets) {
    $Name = $T.Name
    $SrcDir = $T.SrcDir
    $BackupDir = $T.BackupDir

    Write-Host "[$Name] 소스: $SrcDir" -ForegroundColor Yellow
    Write-Host "[$Name] 백업: $BackupDir" -ForegroundColor Yellow

    if (-not (Test-Path $SrcDir)) {
        Write-Host "  ! 소스 폴더 없음 — 스킵" -ForegroundColor Red
        continue
    }

    # 백업 폴더 생성 (존재하지 않으면)
    if (-not $DryRun) {
        if (-not (Test-Path $BackupDir)) {
            New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
            Write-Host "  + 백업 폴더 생성됨" -ForegroundColor Green
        }
    }

    # _백업 폴더 자체는 제외하고 .md만
    $Files = Get-ChildItem -Path $SrcDir -Filter "*.md" -File -Recurse -ErrorAction SilentlyContinue |
             Where-Object { $_.FullName -notmatch "\\_백업\\" -and $_.FullName -notmatch "\\_trash\\" }

    $Total = $Files.Count
    $AllManifest.통계.총파일수 += $Total
    Write-Host "  - 발견: $Total 파일"

    $idx = 0
    foreach ($F in $Files) {
        $idx++
        $RelPath = $F.FullName.Substring($SrcDir.Length).TrimStart('\')
        # 파일명에 .pre_normalize 접미사
        $BaseName = [IO.Path]::GetFileNameWithoutExtension($F.Name)
        $NewName = "${BaseName}.pre_normalize.md"
        # 하위 폴더 보존
        $RelDir = Split-Path $RelPath -Parent
        $DestDir = if ($RelDir) { Join-Path $BackupDir $RelDir } else { $BackupDir }
        $DestPath = Join-Path $DestDir $NewName

        # 진행률 출력 (10파일마다)
        if ($idx % 10 -eq 0 -or $idx -eq $Total) {
            $pct = [math]::Round(($idx / $Total) * 100, 1)
            Write-Host "    [$idx/$Total] $pct% — $($F.Name)" -ForegroundColor Gray
        }

        $entry = @{
            원본 = $F.FullName
            백업 = $DestPath
            크기_바이트 = $F.Length
            수정시각 = $F.LastWriteTime.ToString("yyyy-MM-ddTHH:mm:ss")
            카테고리 = $Name
        }

        try {
            if ($DryRun) {
                $entry.상태 = "dry-run"
                $AllManifest.통계.스킵++
            } else {
                # 백업 대상이 이미 존재하면 스킵
                if (Test-Path $DestPath) {
                    $entry.상태 = "이미존재—스킵"
                    $AllManifest.통계.스킵++
                } else {
                    if (-not (Test-Path $DestDir)) {
                        New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
                    }
                    Copy-Item -Path $F.FullName -Destination $DestPath -Force
                    $entry.상태 = "성공"
                    $AllManifest.통계.성공++
                }
            }
        } catch {
            $entry.상태 = "실패: $($_.Exception.Message)"
            $AllManifest.통계.실패++
            Write-Host "    ! 실패: $($F.Name) — $($_.Exception.Message)" -ForegroundColor Red
        }

        $AllManifest.파일목록 += $entry
    }

    Write-Host ""
}

# 매니페스트 저장
if (-not (Test-Path $MetaDir)) {
    New-Item -ItemType Directory -Path $MetaDir -Force | Out-Null
}
if (-not $DryRun) {
    $AllManifest | ConvertTo-Json -Depth 10 | Out-File -FilePath $ManifestPath -Encoding utf8
    Write-Host "+ 매니페스트 저장: $ManifestPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " 백업 결과 요약" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " 총파일수 : $($AllManifest.통계.총파일수)"
Write-Host " 성공     : $($AllManifest.통계.성공)" -ForegroundColor Green
Write-Host " 스킵     : $($AllManifest.통계.스킵)" -ForegroundColor Yellow
Write-Host " 실패     : $($AllManifest.통계.실패)" -ForegroundColor Red
Write-Host ""
if ($DryRun) {
    Write-Host " DRY-RUN 모드 — 실제 복사 없음. 실행하려면 -DryRun 옵션 제거." -ForegroundColor Yellow
} else {
    Write-Host " 백업 완료. 다음 단계: normalize_송영곤_A형.py --dry-run" -ForegroundColor Green
}
Write-Host ""
