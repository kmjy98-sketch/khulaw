---
name: transcript-tools
description: 전사문 분할 및 처리 도구. 긴 전사문 분할, 파트 나누기. "전사문 분할", "파일 나눠줘", "split" 요청 시 사용.
---

# 전사문 도구 Skill

<!-- @rule: AGENTS.md#17 Verify-Before-Act -->
<!-- @rule: AGENTS.md#17 Verify-Before-Act -->
<!-- @rule: GEMINI.md#17 Verify-Before-Act -->

## Quick Start

전사문 분할:

```powershell
python .agent/skills/transcript-tools/scripts/split_transcript.py <transcript.md> [--parts 10]
```

---

## 주요 기능

### 전사문 분할

```powershell
python scripts/split_transcript.py <file> [--parts N] [--output <dir>]
```

**옵션:**

- `--parts, -p`: 분할 개수 (기본: 10)
- `--output, -o`: 출력 폴더

**예시:**

```powershell
# 10개로 분할
python scripts/split_transcript.py "전사문.md" -p 10 -o "split/"
```

---

## 출력 형식

```
split/
├── 전사문_part01.md
├── 전사문_part02.md
├── ...
└── 전사문_part10.md
```

---

## 워크플로우 연계

1. **전사** → whisper-transcribe Skill
2. **분할** → transcript-tools Skill
3. **교정** → `transcript-correction` Skill (`/transcribe`, 파트별)

---

## Gemini 위임 금지 (2026-04-27)

전사문 **분할·재구성·요약 작업은 Gemini에 위임 금지**합니다.

- **이유**: 2026-04-XX 파일럿에서 Gemini가 전사 청크를 silent drop(예외 없이 누락)하는 사례 확인.
- **적용 범위**: split_transcript.py 결과 재정렬, 청크 병합, 부분 요약 모두.
- **대체**: 본 Python 스크립트(deterministic) 또는 Claude Code(검증 가능)로 처리.
- **참조**: `~/.gemini/GEMINI.md` §0 Gemini 역할 (탐색 전용 고정).

