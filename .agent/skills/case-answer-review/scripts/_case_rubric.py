# -*- coding: utf-8 -*-
"""_case_rubric.py — 사례답안 가중 루브릭 채점 (Q2-1 파일럿).

배경: render_case_answer_review.provisional_grade()는 coverage 단일 지표만 쓴다.
case-answer-review SKILL의 가중 루브릭(쟁점0.25/키워드0.20/구조0.20/결론0.15/포섭0.20)을
코드로 구현한다. 근거(입력) 없는 항목은 보류(None)로 두고 가중에서 제외·재정규화한다
(#1·#2: source 없는 감점 금지). 출력은 0.0~1.0 + 항목별 점수 + O/△/X 등급.

순수 함수 — state 파일·외부 의존 없음. 시스템 유틸리티(#30 면제).
"""

WEIGHTS = {
    "issue": 0.25,       # 쟁점 발견
    "keyword": 0.20,     # 키워드 일치
    "structure": 0.20,   # 구조(목차) 일치
    "conclusion": 0.15,  # 결론 일치
    "application": 0.20,  # 포섭(사실↔법리)
}

# 항목 점수 → SRS review_type·due. 출처: spaced-repetition SKILL "채점 연동 간격".
_REVIEW_RULES = [
    ("issue", lambda s: s < 0.5, "issue_spotting"),
    ("conclusion", lambda s: s <= 0.0, "conclusion_drill"),
    ("keyword", lambda s: s < 0.5, "keyword_recall"),
    ("structure", lambda s: s < 0.5, "outline_recall"),
    ("application", lambda s: s < 0.6, "mini_application"),
]


def _has(answer, token):
    return bool(token) and token.lower() in answer


def _issue_score(answer, expected_issues):
    """각 쟁점: 명칭 발견 1.0 / 별칭만 0.5 / 누락 0.0 의 평균. 입력 없으면 보류(None)."""
    if not expected_issues:
        return None
    scores = []
    for item in expected_issues:
        if isinstance(item, (list, tuple)):
            name, aliases = item[0], list(item[1:][0]) if len(item) > 1 else []
        else:
            name, aliases = item, []
        if _has(answer, name):
            scores.append(1.0)
        elif any(_has(answer, a) for a in aliases):
            scores.append(0.5)
        else:
            scores.append(0.0)
    return sum(scores) / len(scores) if scores else None


def _ratio_score(answer, items):
    """항목 중 답안에 등장한 비율. 입력 없으면 보류(None)."""
    if not items:
        return None
    hit = sum(1 for it in items if _has(answer, it))
    return hit / len(items)


def _conclusion_score(answer, patterns, opposite_patterns=None):
    """반대결론 0.0 / 정확일치 1.0 / 그 외(부분) 0.5. patterns 없으면 보류."""
    if not patterns:
        return None
    if opposite_patterns and any(_has(answer, p) for p in opposite_patterns):
        return 0.0
    if any(_has(answer, p) for p in patterns):
        return 1.0
    return 0.5


def _application_score(answer, facts, has_legal):
    """포섭 휴리스틱: 사실 인용 비율. 단 법리만 있고 사실 0이면 최대 0.5,
    핵심사실 일부 누락이면 최대 0.6 (SKILL 루브릭). facts 없으면 보류."""
    if not facts:
        return None
    ratio = sum(1 for f in facts if _has(answer, f)) / len(facts)
    if ratio == 0.0:
        return 0.5 if has_legal else 0.0
    if ratio < 1.0:
        return min(ratio, 0.6)
    return 1.0


def score_rubric(*, answer_norm, expected_issues=None, required_keywords=None,
                 answer_structure=None, conclusion_patterns=None,
                 opposite_conclusion_patterns=None, application_facts=None):
    """가중 루브릭 채점. 근거 없는 항목은 보류(제외·재정규화)."""
    a = (answer_norm or "").lower()
    if not a.strip():
        return {"score": None, "grade": "보류", "items": {}, "review_suggestions": []}

    raw = {
        "issue": _issue_score(a, expected_issues),
        "keyword": _ratio_score(a, required_keywords),
        "structure": _ratio_score(a, answer_structure),
        "conclusion": _conclusion_score(a, conclusion_patterns, opposite_conclusion_patterns),
        "application": _application_score(a, application_facts, bool(required_keywords and _ratio_score(a, required_keywords))),
    }

    items, active_w, weighted = {}, 0.0, 0.0
    for name, w in WEIGHTS.items():
        s = raw[name]
        if s is None:
            items[name] = {"score": None, "weight": w, "status": "보류"}
            continue
        items[name] = {"score": round(s, 2), "weight": w, "status": "채점"}
        active_w += w
        weighted += s * w

    if active_w == 0:
        return {"score": None, "grade": "보류", "items": items, "review_suggestions": []}

    score = weighted / active_w  # 보류 항목 제외 후 재정규화
    grade = "O" if score >= 0.8 else "△" if score >= 0.5 else "X"

    suggestions = []
    for name, trigger, rtype in _REVIEW_RULES:
        s = raw[name]
        if s is not None and trigger(s):
            suggestions.append(rtype)
    if not suggestions:
        suggestions.append("stable")

    return {"score": round(score, 3), "grade": grade, "items": items,
            "review_suggestions": suggestions}
