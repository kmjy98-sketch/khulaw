@echo off
setlocal
chcp 65001 > nul

set "SRC_DIR=h:\내 드라이브\민사"
set "DEST_DIR=h:\내 드라이브\.agent\data\pdf_extracts"
set "SCRIPT=h:\내 드라이브\.agent\skills\socratic-loader\scripts\batch_extract.py"

if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"

echo.
echo [Missing Batch] 미처리 PDF 추출 (1-2 ~ 1-9, 2~5)
echo --------------------------------------------------------
:: Yoon Dong-hwan series 1-2 to 1-9
python "%SCRIPT%" "%SRC_DIR%" "%DEST_DIR%" --chunk-size 30 --pattern "**/1-[2-9]_*.pdf"

:: Other series
python "%SCRIPT%" "%SRC_DIR%" "%DEST_DIR%" --chunk-size 30 --pattern "**/2-*.pdf"
python "%SCRIPT%" "%SRC_DIR%" "%DEST_DIR%" --chunk-size 30 --pattern "**/3-*.pdf"
python "%SCRIPT%" "%SRC_DIR%" "%DEST_DIR%" --chunk-size 30 --pattern "**/4-*.pdf"
python "%SCRIPT%" "%SRC_DIR%" "%DEST_DIR%" --chunk-size 30 --pattern "**/5-*.pdf"

echo.
echo ========================================================
echo 미처리 추출 작업 완료!
echo 저장 위치: %DEST_DIR%
echo ========================================================
pause
