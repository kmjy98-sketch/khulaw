@echo off
REM Whisper.cpp 배치 전사 스크립트
REM 사용법: transcribe_batch.bat [폴더경로]
REM 지원 형식: wav, mp3, m4a, flac, ogg

setlocal enabledelayedexpansion

set WHISPER_DIR=%~dp0
set MODEL_PATH=%WHISPER_DIR%models\ggml-small.bin
set WHISPER_EXE=%WHISPER_DIR%bin\Release\whisper-cli.exe

if "%~1"=="" (
    echo =============================================
    echo  Whisper.cpp 배치 전사 스크립트
    echo =============================================
    echo.
    echo 사용법: transcribe_batch.bat [폴더경로]
    echo 예시: transcribe_batch.bat "C:\강의"
    echo.
    echo 지원 형식: wav, mp3, m4a, flac, ogg
    exit /b 1
)

if not exist "%MODEL_PATH%" (
    echo [오류] 모델 파일이 없습니다: %MODEL_PATH%
    echo 다음 명령으로 다운로드하세요:
    echo curl -L -o "%MODEL_PATH%" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
    exit /b 1
)

set COUNT=0
set DONE=0
set SKIPPED=0

echo =============================================
echo  배치 전사 시작: %~1
echo  모델: ggml-small (한국어)
echo =============================================
echo.

REM 파일 개수 세기
for %%E in (wav mp3 m4a flac ogg) do (
    for %%F in ("%~1\*.%%E") do (
        if exist "%%F" set /a COUNT+=1
    )
)

echo [발견] %COUNT%개 오디오 파일
echo.

REM 전사 실행
for %%E in (wav mp3 m4a flac ogg) do (
    for %%F in ("%~1\*.%%E") do (
        if exist "%%F" (
            set "OUTFILE=%%~dpnF_transcript.txt"
            
            if exist "!OUTFILE!" (
                echo [건너뜀] %%~nxF ^(이미 전사됨^)
                set /a SKIPPED+=1
            ) else (
                echo.
                echo =============================================
                set /a DONE+=1
                echo [!DONE!/%COUNT%] %%~nxF
                echo =============================================
                
                "%WHISPER_EXE%" -m "%MODEL_PATH%" -l ko -otxt -of "%%~dpnF_transcript" "%%F"
                
                if exist "!OUTFILE!" (
                    echo [완료] 저장됨: %%~nF_transcript.txt
                ) else (
                    echo [오류] 전사 실패: %%~nxF
                )
            )
        )
    )
)

echo.
echo =============================================
echo  배치 전사 완료
echo  처리: %DONE%개 / 건너뜀: %SKIPPED%개 / 총: %COUNT%개
echo =============================================

endlocal
