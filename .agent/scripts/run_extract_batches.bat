@echo off
setlocal
chcp 65001 > nul

:: ========================================================
:: PDF 배치 추출 스크립트 (민사 전체 - 재귀적 탐색)
:: ========================================================

set "SRC_DIR=h:\내 드라이브\민사"
set "DEST_DIR=h:\내 드라이브\.agent\data\pdf_extracts"
set "SCRIPT=h:\내 드라이브\.agent\skills\socratic-loader\scripts\batch_extract.py"

if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"

echo.
echo [Batch 1] 기본 이론서 추출 (1-00 ~ 1-05)
echo - 탐색 경로: %SRC_DIR%\**
echo --------------------------------------------------------
python "%SCRIPT%" "%SRC_DIR%" "%DEST_DIR%" --chunk-size 30 --pattern "**/1-0[0-5]*.pdf"

echo.
echo [일시 정지] Batch 1 완료. 계속하려면 아무 키나 누르세요...
pause > nul

echo.
echo [Batch 2] 심화 이론서 추출 (1-06 ~ 1-11)
echo --------------------------------------------------------
python "%SCRIPT%" "%SRC_DIR%" "%DEST_DIR%" --chunk-size 30 --pattern "**/1-0[6-9]*.pdf"
python "%SCRIPT%" "%SRC_DIR%" "%DEST_DIR%" --chunk-size 30 --pattern "**/1-1*.pdf"

echo.
echo [일시 정지] Batch 2 완료. 계속하려면 아무 키나 누르세요...
pause > nul

echo.
echo [Batch 3] 문제집 추출 (3-*, 4-*)
echo --------------------------------------------------------
python "%SCRIPT%" "%SRC_DIR%" "%DEST_DIR%" --chunk-size 30 --pattern "**/*[34]-*.pdf"

echo.
echo ========================================================
echo 모든 추출 작업 완료!
echo 저장 위치: %DEST_DIR%
echo ========================================================
pause
