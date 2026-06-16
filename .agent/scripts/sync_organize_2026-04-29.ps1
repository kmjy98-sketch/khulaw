# sync 정리 스크립트 (2026-04-29)
# 자소서·발제 메타 산출물 9건을 백업 폴더로 이동
# 사용법: PowerShell에서 실행
#   cd "H:\내 드라이브"
#   powershell -ExecutionPolicy Bypass -File .\sync_organize_2026-04-29.ps1

$ErrorActionPreference = "Stop"
$base = "H:\내 드라이브\sync"

# 1. 백업 폴더 생성
$dest_jaso = Join-Path $base "로펌_자소서\_백업\2026-04-28\메타산출물"
$dest_balje = Join-Path $base "_발제\백업\2026-04-28\메타산출물"
New-Item -ItemType Directory -Force -Path $dest_jaso  | Out-Null
New-Item -ItemType Directory -Force -Path $dest_balje | Out-Null
Write-Host "[OK] 백업 폴더 준비 완료"

# 2. 자소서 메타 산출물 7건 이동
$jaso_files = @(
    "율촌_초안_보완_후보.md",
    "율촌_초안_윤문검토_v1.md",
    "율촌_초안_IV발전연구_보완_후보.md",
    "율촌_초안_IV재작성안_v1.md",
    "율촌_초안_II2.4_II2.5_통합안_v2.md",
    "율촌_초안_보완_후보_v2_로펌톤.md",
    "율촌_초안_v2_적용보고.md"
)
foreach ($f in $jaso_files) {
    $src = Join-Path $base "로펌_자소서\$f"
    if (Test-Path $src) {
        Move-Item -Path $src -Destination $dest_jaso -Force
        Write-Host "  [MV] $f"
    } else {
        Write-Host "  [SKIP] $f (없음)"
    }
}

# 3. 발제 윤문검토 메타 산출물 2건 이동
$balje_files = @(
    "상법개정안_고려아연_윤문검토_v1.md",
    "군부대_민간위탁_윤문검토_v1.md"
)
foreach ($f in $balje_files) {
    $src = Join-Path $base "_발제\윤문검토\$f"
    if (Test-Path $src) {
        Move-Item -Path $src -Destination $dest_balje -Force
        Write-Host "  [MV] $f"
    } else {
        Write-Host "  [SKIP] $f (없음)"
    }
}

Write-Host ""
Write-Host "이동 완료 — 자소서 7건 + 발제 2건 = 총 9건"
Write-Host ""
Write-Host "잔존(KEEP) 검증:"
Get-ChildItem "$base\로펌_자소서\" -File | Select-Object Name, Length | Format-Table -AutoSize
Get-ChildItem "$base\_발제\" -File | Select-Object Name, Length | Format-Table -AutoSize
Get-ChildItem "$base\_발제\윤문검토\" -File | Select-Object Name, Length | Format-Table -AutoSize
