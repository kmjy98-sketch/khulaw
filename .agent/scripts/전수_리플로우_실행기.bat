@echo off
chcp 65001 >nul
color 0A
echo ========================================================
echo        법학 교재 마크다운 전수 리플로우 자동화 도구
echo ========================================================
echo.
echo 대상 폴더: H:\내 드라이브\sync\_교재원문\
echo 남은 원문 파일들을 Gemini API를 통해 백그라운드로 자동 구조화합니다.
echo.

cd /d "H:\내 드라이브\sync\_교재원문"

IF "%GEMINI_API_KEY%"=="" (
    echo [주의] 시스템 환경변수에 GEMINI_API_KEY가 없습니다.
    set /p GEMINI_API_KEY="본인의 Gemini API Key를 입력 후 엔터를 눌러주세요: "
    echo.
)

echo [시스템] 리플로우 스크립트를 백그라운드로 시작합니다...
echo (창을 닫으셔도 프로세스가 계속 진행될 수 있으나, 가급적 이 창을 띄워두세요)
echo.
python _reflow_global_batch.py
pause
