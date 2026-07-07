# 파일 이름 변경 스크립트
# 규칙: (유형번호-순서)과목_강사_강의명_(유형) - 순서는 2자리(01~99)
$ErrorActionPreference = "SilentlyContinue"

# ====== 1. 진행중/교재 폴더 ======
$path1 = "H:\내 드라이브\민사\진행중\교재"

$renames1 = @{
    "(1)[송영곤 변호사] 최고와 소멸시효.pdf"                               = "(2-05)민법_송영곤_최고와소멸시효_(정리).pdf"
    "(2-1)[송영곤 변호사] 2026 민법기본강의 주요사례(2)-25.12.23..pdf"        = "(3-01)민법_송영곤_기본민강_주요사례2_(사례).pdf"
    "(3-1)[송영곤 변호사] 2025 민법기본강의 주요사례(3)-25.12.31..pdf"        = "(3-02)민법_송영곤_기본민강_주요사례3_(사례).pdf"
    "(3-1)[송영곤 변호사] 2026 기본민강-dt-선택형(3차)-25.12.18..pdf"       = "(4-03)민법_송영곤_기본민강_DT선택형3차_(선택).pdf"
    "(3-1)[송영곤 변호사] 2026 기본민법강의 주요쟁점 개관 자료(2차)-25.12.25..pdf" = "(2-06)민법_송영곤_기본민강_주요쟁점개관2차_(정리).pdf"
    "(4-1)[송영곤 변호사] 2026 기본민강-dt-선택형(4차)-25.12.20..pdf"       = "(4-04)민법_송영곤_기본민강_DT선택형4차_(선택).pdf"
    "(5-1)[송영곤 변호사] 2026 기본민강-dt-선택형(5차)-25.12.22..pdf"       = "(4-05)민법_송영곤_기본민강_DT선택형5차_(선택).pdf"
    "(6-1)[송영곤 변호사] 2026 기본민강-선택형자료(6)-25.12.25.자.pdf"        = "(4-06)민법_송영곤_기본민강_선택형6_(선택).pdf"
    "(7-1)[송영곤 변호사] 2026 기본민강-선택형자료(7)-25.12.31.자.pdf"        = "(4-07)민법_송영곤_기본민강_선택형7_(선택).pdf"
    "(8-1) [송영곤 변호사] 2026 기본민강-선택형자료(8)-26.1.2..pdf"          = "(4-08)민법_송영곤_기본민강_선택형8_(선택).pdf"
    "(9-1)[송영곤 변호사] 2026 기본민강-선택형자료(9)-26.1.5.자.pdf"          = "(4-09)민법_송영곤_기본민강_선택형9_(선택).pdf"
}

foreach ($old in $renames1.Keys) {
    $oldPath = Join-Path $path1 $old
    $newName = $renames1[$old]
    if (Test-Path $oldPath) {
        Rename-Item -LiteralPath $oldPath -NewName $newName -Force
        Write-Host "[OK] $old -> $newName"
    }
}

# 중복 파일 삭제
$dup = Join-Path $path1 "(3-1)[송영곤 변호사] 2026 기본민강-dt-선택형(3차)-25.12.18. (1).pdf"
if (Test-Path $dup) { Remove-Item -LiteralPath $dup -Force; Write-Host "[DEL] 중복 파일 삭제" }

# ====== 2. 보관/송영곤 dt 폴더 ======
$path2 = "H:\내 드라이브\민사\보관\송영곤 dt"
1..10 | ForEach-Object {
    $n = $_
    $nn = $n.ToString("00")  # 2자리 포맷
    $oldQ = "민법_송영곤_DT_${n}회_문제*.pdf"
    $oldA = "민법_송영곤_DT_${n}회_해설.pdf"
    
    Get-ChildItem -Path $path2 -Filter $oldQ | ForEach-Object {
        Rename-Item -LiteralPath $_.FullName -NewName "(4-$nn)민법_송영곤_DT${n}회_문제_(선택).pdf" -Force
        Write-Host "[OK] DT ${n}회 문제"
    }
    $aPath = Join-Path $path2 $oldA
    if (Test-Path $aPath) {
        Rename-Item -LiteralPath $aPath -NewName "(4-$nn)민법_송영곤_DT${n}회_해설_(선택).pdf" -Force
        Write-Host "[OK] DT ${n}회 해설"
    }
}

# ====== 3. 보관 루트 폴더 ======
$path3 = "H:\내 드라이브\민사\보관"

$renames3 = @{
    "민법_JJMT_민법_계산_요소_정리.pdf"     = "(2-01)민법_JJMT_계산요소정리_(정리).pdf"
    "민법_곽낙규_진도별_변사기_민법사례연습.pdf"   = "(1-01)민법_곽낙규_민법사례연습_(교재).pdf"
    "민법_민법의_맥_기초(최종)25.12.06.pdf" = "(2-02)민법_윤동환_민법의맥기초_(정리).pdf"
    "민법_민법의_해석.pdf"               = "(1-02)민법__민법의해석_(교재).pdf"
    "민법_박승수_민법기본사례.pdf"           = "(1-03)민법_박승수_민법기본사례_(교재).pdf"
    "민법_송영곤_민사법사례연습2_민법.pdf"      = "(1-04)민법_송영곤_민사법사례연습2_(교재).pdf"
}

foreach ($old in $renames3.Keys) {
    $oldPath = Join-Path $path3 $old
    $newName = $renames3[$old]
    if (Test-Path $oldPath) {
        Rename-Item -LiteralPath $oldPath -NewName $newName -Force
        Write-Host "[OK] $old -> $newName"
    }
}

Write-Host "`n====== 변경 완료 ======"
