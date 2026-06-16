# 해커스변호사 헌법 사례형 PDF — 명명규칙 적용 + OCR 큐 배치
# 작성: 2026-04-29
# 원칙: CLAUDE.md #15 (Verify-Before-Act), #16 (삭제 금지 — Move만)

$ErrorActionPreference = 'Stop'

$src = "H:\내 드라이브\3.공법\[5+1] 2027 해커스변호사 변호사시험 기출문제집 헌법 사례형 - 최신개정판ㅣ변호사시험 등 각종 국가고_3c_r6_d2.pdf"
$dstDir = "H:\내 드라이브\3.공법\91.보관\해커스변호사_헌법사례형\사례"
$dstName = "해커스변호사_변호사시험기출_헌법사례형.pdf"
$dst = Join-Path $dstDir $dstName

Write-Host "[1/4] 원본 확인" -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath $src)) {
    Write-Host "  원본 없음: $src" -ForegroundColor Red
    exit 1
}
$srcInfo = Get-Item -LiteralPath $src
Write-Host ("  크기: {0:N0} bytes ({1:N1} MB)" -f $srcInfo.Length, ($srcInfo.Length/1MB))

Write-Host "[2/4] 대상 폴더 생성" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
Write-Host "  $dstDir"

Write-Host "[3/4] 충돌 확인" -ForegroundColor Cyan
if (Test-Path -LiteralPath $dst) {
    Write-Host "  대상 이미 존재 — 작업 중단 (수동 확인 필요): $dst" -ForegroundColor Yellow
    exit 2
}

Write-Host "[4/4] Move (이름 변경 + 이동)" -ForegroundColor Cyan
Move-Item -LiteralPath $src -Destination $dst -Verbose
Write-Host "  → $dst" -ForegroundColor Green

Write-Host "`n완료. 백업본 (그대로 유지):" -ForegroundColor Green
Write-Host "  H:\내 드라이브\0.공유드라이브\헌법스-타디\[5+1] 2027 해커스변호사 변호사시험 기출문제집 헌법 사례형 - 최신개정판ㅣ변호사시험 등 각종 국가고_3c_r6_d2.pdf"

Write-Host "`nOCR 큐: 3.공법/ 하위 PDF는 ocr_extract_v2.ipynb 가 자동 픽업합니다." -ForegroundColor Cyan
