---
name: whisper-transcribe
description: 음성/영상 파일 전사(STT) 요청 시 사용. 트리거: "전사", "받아쓰기", "음성 변환", "transcribe", "STT"
---

`E:\법학볼트\.agent\skills\whisper-transcribe\SKILL.md` 를 읽고 지침을 따른다.

로컬 Whisper 우선 경로: `.agent/skills/whisper-transcribe/scripts/transcribe.bat` (신규 추출은 LlamaParse 로컬화 — Colab 폐기).
전사 완료 후 `transcript-tools` → `transcript-correction` 순서로 후처리한다.
