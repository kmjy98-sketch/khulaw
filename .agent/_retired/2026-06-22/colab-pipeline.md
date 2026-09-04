---
description: Colab 녹음 전사 자동화 - 녹음 업로드 → 전사 → 분할 → 벡터DB → 진도 관리
---

# Colab 전사 자동화 파이프라인

> 녹음 파일을 올려두고 Colab 실행 → 전사/분할/인덱싱/진도까지 자동 처리

---

## 사용법 (2단계)

### Step 1: 녹음 파일 업로드

```
H:\내 드라이브\5.기타\_inbox\녹음\   ← 여기에 녹음 파일 드래그 앤 드롭
```

지원 형식: mp3, wav, m4a, mp4, webm, flac, ogg, aac

### Step 2: Colab 전사 실행

1. [Colab 노트북 열기](https://colab.research.google.com/) → 업로드 또는 Drive에서 열기
   - 경로: `내 드라이브/.agent/skills/whisper-transcribe/colab_transcribe.ipynb`
2. **런타임 → 런타임 유형 변경 → GPU (T4)**
3. **런타임 → 모두 실행** (Ctrl+F9)

// turbo

### Step 3: 후처리 (로컬)

```powershell
python "h:\내 드라이브\.agent\skills\whisper-transcribe\scripts\post_transcribe.py"
```

---

## 폴더 구조

```
5.기타/_inbox/녹음/
├── (녹음 파일을 여기에 업로드)
├── output/        ← Colab 전사 결과 임시 저장
└── processed/     ← 전사 완료된 원본/전사본 자동 이동
```

---

## 녹음파일명 규칙

> 녹음 시 약어 사용 → 전사 파이프라인에서 ASCII alias 규칙으로 canonical 변환
> 운영 규칙 저장: `.agent/state/transcript_alias_rules.json`

| 약어 | ASCII alias | 강의 | 전사문 저장 경로 |
|------|-------------|------|----------------|
| `헌1` | `pub_lee_h1` | 헌법원리1 이진 | `3.공법/10.이진_헌법원리1/전사문/` |
| `공법` | `pub_kang_admin` | 행정법 강성민 | `3.공법/20.강성민_행정법/전사문/` |
| `형1` | `crm_seo_cr1` | 형법1 서보학 | `2.형사/20.서보학_형법1/전사문/` |
| `형사` | `crm_kim_cr1` | 형법교안 | `2.형사/10.김기용_형법교안/전사문/` |
| `민1` | `civ_kang_m1` | 민법1 강혜림 | `1.민사/10.강혜림_민법1/전사문/` |
| `민3` | `civ_jeon_m3` | 민법3 전경운 | `1.민사/20.전경운_민법3/전사문/` |
| `국제` | `opt_intl` | 국제법총론 | `4.선택법/20.국제법총론/전사문/` |
| `윤리` | `opt_eth` | 법조윤리 | `4.선택법/10.법조윤리/전사문/` |

- 원본 저장: 후처리 시 각 회차 폴더(`.../전사문/{ascii_alias}_{회차}/`)에 canonical `*_transcript.txt` 원본을 함께 저장
- 미매칭 파일명: `5.기타/_inbox/녹음/unmatched_transcripts/misc_audio/` 기준으로 저장 후 수동 정리
- 처리완료 전사본: `5.기타/_inbox/녹음/processed/transcripts/{YYYY-MM-DD}/`로 canonical 파일명으로 자동 이동

---

## 파이프라인 흐름

```
녹음 업로드 → [Colab] 전사 → [로컬] 원본저장+분할 → 벡터DB → 진도 업데이트
                                ↓
                 transcript-correction Skill (/transcribe)
                                ↓
                         수업노트 정리 (/lecture-notes)
```

---

## 옵션

```powershell
# 드라이런 (실행 없이 확인만)
python "h:\내 드라이브\.agent\skills\whisper-transcribe\scripts\post_transcribe.py" --dry-run

# 분할만 건너뛰기
python "h:\내 드라이브\.agent\skills\whisper-transcribe\scripts\post_transcribe.py" --skip-split

# 벡터DB 인덱싱만 건너뛰기
python "h:\내 드라이브\.agent\skills\whisper-transcribe\scripts\post_transcribe.py" --skip-index

# 파트 수 변경 (기본 10)
python "h:\내 드라이브\.agent\skills\whisper-transcribe\scripts\post_transcribe.py" --parts 5
```

---

## 성능 참고

| 강의 길이 | Colab 전사 시간 | 모델 |
|-----------|----------------|------|
| 30분 | ~1.5분 | large-v3 (T4 GPU) |
| 1시간 | ~3분 | large-v3 (T4 GPU) |
| 1.5시간 | ~5분 | large-v3 (T4 GPU) |
| 3시간 | ~10분 | large-v3 (T4 GPU) |

---

## 연계 워크플로우

| 단계 | 도구 |
|------|------|
| 전사 | `colab_transcribe.ipynb` (Colab) |
| 후처리 | `post_transcribe.py` (로컬) |
| 교정 | `transcript-correction` Skill (`/transcribe`) |
| 정리 | `/lecture-notes` 워크플로우 |
| 문답 | `/socratic` 워크플로우 |
