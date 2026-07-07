# _inbox 분류 스크립트
# 실행 경로: h:\내 드라이브

$inbox = "h:\내 드라이브\_inbox"
$targets = @{
    "LEET_MOCK" = "h:\내 드라이브\로스쿨\LEET\모의고사"
    "LEET_BOOK" = "h:\내 드라이브\로스쿨\LEET\교재"
    "LEET_NOTE" = "h:\내 드라이브\로스쿨\LEET\정리"
    "UNIV"      = "h:\내 드라이브\기타\대학"
    "DT"        = "h:\내 드라이브\민사\진행중\필기"
}

# 1. 대상 폴더 생성
foreach ($path in $targets.Values) {
    if (!(Test-Path $path)) { New-Item -ItemType Directory -Path $path -Force | Out-Null }
}

# 2. 대학 자료 이동
$univPatterns = @("*201802455*", "*주차*", "*강의*", "*녹음*", "*기말*", "*중간*", "*과제*", "*윤리*", "*개발협력*", "*재무*", "*잼관*", "*경제*", "*농지개혁*", "*보고서*", "*학기*")
foreach ($pattern in $univPatterns) {
    Get-ChildItem "$inbox\$pattern" | Move-Item -Destination $targets["UNIV"] -Force -ErrorAction SilentlyContinue
}

# 3. LEET 모의고사 이동
$mockPatterns = @("*FINAL*", "*파이널*", "*법저*", "*해커스*", "*시대법저*", "*모의고사*")
foreach ($pattern in $mockPatterns) {
    Get-ChildItem "$inbox\$pattern" | Move-Item -Destination $targets["LEET_MOCK"] -Force -ErrorAction SilentlyContinue
}

# 4. LEET 교재류 이동
$bookPatterns = @("*두뇌보완계획*", "*코어코드*", "*온톨로지*", "*강화약화*", "*법철학*", "*논리*", "*프린시플*", "*법률문장론*")
foreach ($pattern in $bookPatterns) {
    Get-ChildItem "$inbox\$pattern" | Move-Item -Destination $targets["LEET_BOOK"] -Force -ErrorAction SilentlyContinue
}

# 5. DT 선택형 자료 이동
Get-ChildItem "$inbox\DT*.pdf" | Move-Item -Destination $targets["DT"] -Force -ErrorAction SilentlyContinue

# 6. 중복 파일 삭제 (파일명 끝에 _1, (1) 등)
$dupPatterns = @("*_1.*", "*_2.*", "*(1).*", "*(2).*")
foreach ($pattern in $dupPatterns) {
    Get-ChildItem "$inbox\$pattern" | Remove-Item -Force -ErrorAction SilentlyContinue
}

Write-Host "=== _inbox 분류 완료 ==="
