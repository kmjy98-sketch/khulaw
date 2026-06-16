---
name: spaced-repetition
description: 간격 반복(SM-2) 복습 스케줄러. "복습 주기 계산", "오늘 복습할 문제", "복습 일정 갱신" 요청 시 사용.
---

# Spaced Repetition Skill

<!-- @rule: AGENTS.md#21 진도 추적 -->
<!-- @rule: AGENTS.md#21 진도 추적 -->
<!-- @rule: GEMINI.md#21 진도 추적 -->

## Quick Start

오늘 복습할 항목 조회:

```powershell
python .agent/skills/spaced-repetition/scripts/srs_scheduler.py --today
```

---

## 주요 기능

### 1. 오늘 복습 항목 조회

```powershell
python scripts/srs_scheduler.py --today
```

### 2. 항목 추가

```powershell
python scripts/srs_scheduler.py --add "불법행위 요건" --topic "민법"
```

### 3. 복습 결과 기록

```powershell
python scripts/srs_scheduler.py --review <item_id> --score <0-5>
```

**점수 기준 (SM-2):**

- 0: 완전 망각
- 1-2: 틀림 (다시 학습 필요)
- 3: 어려웠지만 맞춤
- 4: 맞춤
- 5: 매우 쉬움

### 4. 전체 상태 조회

```powershell
python scripts/srs_scheduler.py --status
```

---

## 알고리즘 (SM-2)

- 정답 시: 간격 = 이전간격 × EF (2.5 기본)
- 오답 시: 간격 초기화 (1일)
- EF 조정: 점수에 따라 0.8~2.5 범위

---

## 답안 채점 연동 간격 (2026-06-16 신설)

case-answer-review 채점 결과를 복습 항목으로 등록할 때, 오류 유형별 초기 간격을 다음으로 둔다(출처: `CODEX_BOOTSTRAP_REPORT.md.md` §19 채택분). 이후 간격은 SM-2가 관리한다.

| 채점 결과 | 초기 due | review_type |
|---|---|---|
| 쟁점 자체를 못 찾음 | D+1 | issue_spotting / outline_recall |
| 결론 반대 | D+1 | conclusion_drill |
| 키워드 50% 미만 | D+2 | keyword_recall |
| 목차 구조 누락 | D+3 | outline_recall |
| 포섭 60점 미만 | D+2 | mini_application |
| 안정적 통과 | D+7 | (정상 SM-2) |
| 2회 연속 양호 | completed 후보 | — |

- 등록은 **사용자가 채점 확정/복습 등록을 지시할 때만** 한다(silent write 금지). case-answer-review는 제안까지만 한다.
- 반복 오답(같은 항목 2회+)은 Anki 카드 후보로도 연동된다 — card-wiki-pipeline §8 준수.

## 데이터 파일

`.agent/state/srs_log.json`에 저장

