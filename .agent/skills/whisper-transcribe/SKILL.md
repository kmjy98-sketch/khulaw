---
name: whisper-transcribe
description: 음성 전사(STT). Colab GPU 전사(추천) 또는 로컬 실행. "전사해줘", "음성 텍스트", "강의 전사", "오디오 변환" 요청 시 사용.
---

# Whisper 전사 Skill

<!-- @rule: AGENTS.md#30 Only-on-Request -->
<!-- @rule: AGENTS.md#30 Only-on-Request -->
<!-- @rule: GEMINI.md#30 Only-on-Request -->

## Quick Start

### ⭐ Colab 전사 (추천)

1. 녹음 파일을 `5.기타/_inbox/녹음/`에 업로드
2. [Colab 노트북](colab_transcribe.ipynb) 실행 (런타임 → GPU → 모두 실행)
3. 후처리:

```powershell
python .agent/skills/whisper-transcribe/scripts/post_transcribe.py
```

> 상세 워크플로우: `/colab-pipeline`

### 로컬 전사 (CPU, 느림)

```powershell
.agent\skills\whisper-transcribe\scripts\transcribe.bat <audio_file>
```

---

## 주요 기능

### Colab 전사 (GPU)

- 엔진: faster-whisper `large-v3`
- 하드웨어: T4 GPU (무료)
- 속도: 1.5시간 강의 → ~5분
- 한국어 정확도: ★★★★★
- 자동 후처리: 분할 → 벡터DB → 진도 관리

### 로컬 단일 파일 전사

```powershell
scripts\transcribe.bat <audio_file>
```

- 지원 형식: mp3, wav, m4a, mp4, webm 등
- 출력: 같은 폴더에 `.txt` 파일 생성

### 로컬 일괄 전사

```powershell
scripts\transcribe_batch.bat <folder_path>
```

- 폴더 내 모든 오디오 파일 전사
- 진행 상황 표시

---

## 모델

| 방식 | 모델 | 속도 | 정확도 |
|------|------|------|--------|
| Colab | large-v3 (float16) | ★★★★★ | ★★★★★ |
| 로컬 | ggml-small | ★★☆☆☆ | ★★★☆☆ |

---

## 워크플로우 연계

1. **전사** → Colab 노트북 또는 로컬 Whisper
2. **후처리** → `post_transcribe.py` (분할/인덱싱/진도)
3. **교정** → `transcript-correction` Skill (`/transcribe`)
4. **정리** → `/lecture-notes` 워크플로우

---

## 참고

- Colab 노트북: `colab_transcribe.ipynb`
- 후처리 스크립트: `scripts/post_transcribe.py`
- Whisper 바이너리 (로컬): `bin/` 폴더
- 자세한 사용법: README.md, `/colab-pipeline` 참조

