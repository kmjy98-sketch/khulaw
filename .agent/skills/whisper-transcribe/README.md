# Whisper.cpp 로컬 STT 설정

## 설치 완료

- 위치: `E:\법학볼트\.agent\whisper\`
- 버전: v1.8.2
- 실행 파일: `bin\Release\whisper-cli.exe`

## 모델 다운로드 (수동)

모델이 없으면 아래 명령 실행:

```powershell
curl -L -o "E:\법학볼트\.agent\whisper\models\ggml-small.bin" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
```

- small 모델: ~466MB, 한국어 정확도 좋음
- 1시간 강의 → ~30분 소요 (CPU)

## 사용법

```cmd
E:\법학볼트\.agent\whisper\transcribe.bat "C:\강의\민법입문.wav"
```

## 출력

- 원본 파일 옆에 `*_transcript.txt` 생성
