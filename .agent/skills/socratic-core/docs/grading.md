# 채점 모드

> 상위 문서: [SKILL.md](../SKILL.md)

---

## 채점표 (Strict Grading)

> **핵심 원칙**: 내용이 맞아도 **필수 요건/키워드가 누락되면 "부분 정답" 또는 "오답"**입니다. 절대 "정답"으로 처리하지 마세요.

| 항목 | 요구 키워드 | 평가 기준 | 근거 |
|------|------------|-----------|------|
| 요건1 | [키워드 A] | 키워드 포함 시 O | 《교재》 p.X |
| 요건2 | [키워드 B] | **누락 시 X (감점)** | 《교재》 p.X |
| 결론 | [인용/기각] | 결론 불일치 시 X | 《교재》 p.X |

### 누락/오답 판정 가이드

1. **Completeness Check (완전성)**:
    - 3가지 요건 중 2가지만 말함 → **부분 정답 (△)** (정답 아님)
    - "나머지 1가지 요건이 빠졌습니다."라고 명확히 지적.

2. **Accuracy Check (정확성)**:
    - 비슷해 보이지만 법적 개념이 틀린 용어 → **오답 (X)**
    - 예: "해제" vs "해지", "무효" vs "취소" 구분 엄격.

---

## SRS 복습 등록 제안 (채점 후, 사용자 확정 시 실행)

**오답/미흡/누락 발생 시 다음을 제안한다(자동 실행하지 않음 — silent write 금지). 사용자가 복습 등록을 지시할 때만 아래 명령을 실행한다:**

```bash
python .agent/skills/spaced-repetition/scripts/srs_scheduler.py --add "[미흡 쟁점/누락 요건]" --topic "[과목]"
```

**평가 점수 기록 (0-5 척도):**

| 상황 | 설명 | 점수 | 명령 |
|------|------|------|------|
| **완전 오답** | 개념 오류, 접근 방식 틀림 | 0-1 | `--score 1` |
| **부분 정답** | **내용은 맞으나 요건 누락**, 용어 부정확 | **2-3** | `--score 3` |
| **완전 정답** | 요건 완벽 구비, 정확한 용어 사용 | 4-5 | `--score 5` |

```bash
python .agent/skills/spaced-repetition/scripts/srs_scheduler.py --review <item_id> --score <0-5>
```

---

## 결론 정리

### 출력 형식

```markdown
## 학습 요약: [주제]

| 항목 | 결론 | 근거 |
|------|------|------|
| 청구/쟁점 | 결론 | 《교재》 p.X |

### 취약점
- [쟁점]에서 오답: [개념] 복습 권장
```

---

## 진도 추적

```
[PROGRESS] topic={주제} done={완료} next={다음}
```

- 형식: `{편}>{장}>{절}>{항목}`
- 저장: `.agent/state/learning.json` (취약점) + `.agent/state/progress.json` (진도)

### 약점 저장/재출제

- 저장: `.agent/state/learning.json` → `weak_points`
- SRS 연동: `.agent/state/srs_log.json` — 자동 기록 금지(silent write 금지). 사용자가 복습 등록/채점 확정을 지시할 때만 spaced-repetition 스킬로 기록(2026-06-16 정책, spaced-repetition·case-answer-review와 동일).
- Spaced Repetition: 간격 조정 (SM-2 알고리즘)
