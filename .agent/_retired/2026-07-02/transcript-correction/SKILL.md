---
name: transcript-correction
description: [RETIRED 2026-06-22 — 명시 요청 시에만] 전사문 교정 독립 스킬. 기존 전사문이나 part 파일을 교재 근거로 교정하고, "전사문 교정", "전사 교정", "/transcribe", "partXX 교정 완료" 요청 시 사용.
---

# Transcript Correction Skill

<!-- @rule: CLAUDE.md#1 Source Grounding -->
<!-- @rule: CLAUDE.md#3 Evidence Mandatory -->
<!-- @rule: CLAUDE.md#15 Verify-Before-Act -->

## Quick Start

1. 교정 대상 전사문 또는 `*_partXX.md`를 확인합니다.
2. 교재/PDF 원문을 근거로 필요한 부분만 엄격 교정합니다.
3. 교정본을 같은 폴더에 `*_corr.md`로 저장합니다.
4. 교정 완료 후 상태를 반영합니다.

```powershell
python .agent/skills/transcript-correction/scripts/mark_corrected.py <corrected_file>
```

예시:

```powershell
python .agent/skills/transcript-correction/scripts/mark_corrected.py "E:\법학볼트\1.민사\강혜림_민법1\전사문\civ_kang_m1_3-1\civ_kang_m1_3-1_part01_corr.md"
```

미교정 목록 확인:

```powershell
python .agent/skills/transcript-correction/scripts/list_uncorrected.py
```

기존 교정본 일괄 반영:

```powershell
python .agent/skills/transcript-correction/scripts/batch_mark_corrected.py
```

---

## 핵심 원칙

### 원문 보존

- 원문 내용 삭제 금지
- 강의 말투, 반복, 강조 표현 유지
- 요약/축약/의역 금지

### 교정 범위

| 허용 | 금지 |
|------|------|
| 명백한 오탈자/기계적 오인식 | 원문 삭제/축약 |
| 전문용어 표기 오류 (조문번호, 판례명) | 말투/문장 구조 변경 |
| 주제 전환 시 헤더 삽입 | 강조/반복 삭제, 요약/의역 |
| 문맥 전환 시 단락 구분 | 내용 재배치/순서 변경 |

### 근거 규칙

- 모든 교정은 근거 2줄 필수
- 근거 발췌: "……"
- 근거 위치: `《문서명》 p.X / 절 / 소제목 / 타임스탬프`

### 불명확 구간

```text
[불명확: 후보1/후보2]
[불명확: 청취불가]
```

- 삭제 금지, 그대로 표기

### 금지 표현

- `(중략)`, `이하 생략`, 임의 생략부호 사용 금지
- 원문에 있는 `…`만 그대로 유지 가능

---

## 출력 형식

기본값:

- 응답에는 교정 로그만 출력
- 전체 교정본은 파일로 저장

교정 로그 형식:

```markdown
## 교정 로그

| 원문 | 교정 | 근거 발췌 | 근거 위치 |
|------|------|----------|----------|
| 이백사십오조 | 제245조 | "민법 제245조 제1항" | 《교재》 p.XX |
```

---

## 완료 처리

`mark_corrected.py`는 다음을 처리합니다.

1. `.agent/state/transcription_log.json`에 교정 완료 상태 기록
2. 파일명에서 `partXX`를 읽을 수 있으면 `progress.py --complete partXX --type transcript` 호출
3. 교정 파일을 `auto-index`에 전달

옵션:

```powershell
python .agent/skills/transcript-correction/scripts/mark_corrected.py <corrected_file> --note "재교정"
python .agent/skills/transcript-correction/scripts/mark_corrected.py <corrected_file> --transcript <raw_transcript.txt>
python .agent/skills/transcript-correction/scripts/mark_corrected.py <corrected_file> --dry-run
```

---

## 연계

1. 전사: `whisper-transcribe`
2. 분할: `transcript-tools`
3. 교정: `transcript-correction`
4. 정리: `study-notes` 또는 `/lecture-notes`
