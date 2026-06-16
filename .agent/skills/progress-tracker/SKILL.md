---
name: progress-tracker
description: 학습 진도 추적. progress.json 관리, 파트 완료 마킹, 현재 범위 조회. "진도 확인", "파트 완료", "범위 설정" 요청 시 사용.
---

# Progress Tracker Skill

<!-- @rule: AGENTS.md#21 진도 추적 -->
<!-- @rule: AGENTS.md#21 진도 추적 -->
<!-- @rule: GEMINI.md#21 진도 추적 -->

> 학습 진도를 `.agent/state/progress.json`에서 통합 관리

---

## Quick Start

```powershell
# 현재 진도 조회
python .agent/skills/progress-tracker/scripts/progress.py --status

# 파트 완료 마킹
python .agent/skills/progress-tracker/scripts/progress.py --complete part01

# 현재 범위 설정
python .agent/skills/progress-tracker/scripts/progress.py --set-scope "교재.pdf" "1-30"
```

---

## 주요 기능

### 1. 진도 조회

```powershell
python scripts/progress.py --status
```

**출력 예시:**

```
[학습 진도]
📖 현재 교재: (1-01)기본민강_권리주체(26).pdf
📄 페이지: 1-30
📝 전사문: part01 (진행중)
📅 마지막 세션: 2026-01-16
```

### 2. 파트 완료 마킹

```powershell
# 전사문 파트 완료
python scripts/progress.py --complete part01 --type transcript

# 수업노트 정리 완료
python scripts/progress.py --complete part05 --type notes
```

### 3. 범위 설정

```powershell
# 새 범위 설정
python scripts/progress.py --set-scope "교재.pdf" "50-80" --transcript "part05.md"
```

### 4. 다음 파트 이동

```powershell
# 다음 파트로 자동 이동
python scripts/progress.py --next
```

---

## 데이터 구조

```json
{
  "current_scope": {
    "textbook": "(1-01)기본민강.pdf",
    "page_range": "1-30",
    "transcript": "part01.md"
  },
  "transcript_parts": {
    "part01": "완료",
    "part02": "진행중"
  },
  "lecture_notes": {
    "기본민법": {
      "range": "part01-10",
      "last_updated": "2026-01-16"
    }
  },
  "last_session": "2026-01-16"
}
```

---

## 워크플로우 연계

| 워크플로우 | 트리거 | 동작 |
|------------|--------|------|
| `/transcribe` | "partXX 교정 완료" | `--complete partXX --type transcript` |
| `/lecture-notes` | "partXX 정리 완료" | `--complete partXX --type notes` |
| `/socratic` | 세션 시작 | `--status` 호출 |

---

## 데이터 파일

| 파일 | 위치 |
|------|------|
| 진도 | `.agent/state/progress.json` |

