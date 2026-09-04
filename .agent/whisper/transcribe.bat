@echo off
REM Whisper.cpp 전사 스크립트
REM 사용법: transcribe.bat [오디오파일경로]

set WHISPER_DIR=%~dp0
set MODEL_PATH=%WHISPER_DIR%models\ggml-small.bin
set WHISPER_EXE=%WHISPER_DIR%bin\Release\whisper-cli.exe

if "%~1"=="" (
    echo 사용법: transcribe.bat [오디오파일경로]
    echo 예시: transcribe.bat "C:\강의\민법입문_1강.wav"
    exit /b 1
)

if not exist "%MODEL_PATH%" (
    echo [오류] 모델 파일이 없습니다: %MODEL_PATH%
    echo 다음 명령으로 다운로드하세요:
    echo curl -L -o "%MODEL_PATH%" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
    exit /b 1
)

echo [시작] 전사 중: %~1
echo [모델] %MODEL_PATH%
echo.

"%WHISPER_EXE%" -m "%MODEL_PATH%" -l ko -otxt -of "%~dpn1_transcript" "%~1"

echo.
echo [완료] 결과 파일: %~dpn1_transcript.txt
