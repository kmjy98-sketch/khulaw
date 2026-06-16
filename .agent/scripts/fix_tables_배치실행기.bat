@echo off
chcp 65001 >nul
color 0B
echo ========================================================
echo        [표 깨짐 복구] 마크다운 전수 리플로우 실행기
echo ========================================================
echo.
echo 대상 파일: 표가 깨지거나 줄글로 변환된 94개 파일 목록
echo Gemini API를 통해 마크다운 표 문법을 정상적으로 복구합니다.
echo.

cd /d "H:\내 드라이브"

IF "%GEMINI_API_KEY%"=="" (
    echo [주의] 시스템 환경변수에 GEMINI_API_KEY가 없습니다.
    set /p GEMINI_API_KEY="본인의 Gemini API Key를 입력 후 엔터를 눌러주세요: "
    echo.
)

echo [시스템] 표 복구 스크립트를 시작합니다...
echo.
python ".agent\scripts\fix_broken_tables_llm.py"
echo.
echo 처리가 완료되었습니다.
pause
