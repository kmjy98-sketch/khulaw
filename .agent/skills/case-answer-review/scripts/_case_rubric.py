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


# ---------------------------------------------------------------------------
# 단위(청구/죄책) 구조 채점 — 요건사실론 정렬 (note-structures.md 정본)
# ---------------------------------------------------------------------------
# 사례집 모범답안에서 추출하는 expected 단위 스키마:
#   unit = {
#     "label": "甲의 丙에 대한 말소등기청구" | "甲의 사기죄",   # 청구권기초 | 죄명
#     "근거": "§214",                          # 근거조문/청구권규범
#     "요건": ["소유권 존재", "丙명의 등기", ...],  # 요건사실 elements = 구조
#     "쟁점": ["대리권남용", ...],               # 다툼 있는 요건 = expected_issues
#     "포섭_사실": ["乙 저가매각", "丙 악의", ...],  # 사안 사실 → 요건 대입 대상
#     "결론": "기각" | "인용" | "유죄" | "무죄",
#     "keywords": ["학설·판례 키워드", ...],      # 선택
#   }
# 민·헌·국 = 청구 단위 / 형 = 죄책 단위. note-structures.md 청구권기초·범죄체계론형과 1:1.

_OPPOSITE = {"인용": "기각", "기각": "인용", "유죄": "무죄", "무죄": "유죄",
             "성립": "불성립", "불성립": "성립", "위헌": "합헌", "합헌": "위헌"}


def score_unit(answer_norm, unit):
    """청구/죄책 단위 1개 채점 → 가중 루브릭(보류 재정규화) + review 제안."""
    a = (answer_norm or "").lower()
    label = unit.get("label", "")
    issues = [label] + list(unit.get("쟁점", [])) if label else list(unit.get("쟁점", []))
    concl = unit.get("결론")
    opp = [_OPPOSITE[concl]] if concl in _OPPOSITE else None
    has_legal = bool(unit.get("요건") and _ratio_score(a, unit["요건"]))

    raw = {
        "issue": _issue_score(a, issues),
        "keyword": _ratio_score(a, unit.get("keywords")),
        "structure": _ratio_score(a, unit.get("요건")),   # 요건사실 열거 여부
        "conclusion": _conclusion_score(a, [concl] if concl else None, opp),
        "application": _application_score(a, unit.get("포섭_사실"), has_legal),  # 포섭(요건별 사실대입)
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

    suggestions = [rtype for name, trig, rtype in _REVIEW_RULES
                   if raw[name] is not None and trig(raw[name])]
    unit_score = None if active_w == 0 else round(weighted / active_w, 3)
    return {"label": label, "score": unit_score, "items": items,
            "review_suggestions": suggestions}


def score_rubric_units(answer_norm, units, unit_type="청구"):
    """청구/죄책 단위 리스트를 단위별 채점 → 평균 집계. note-structures.md 구조 정렬."""
    if not (answer_norm or "").strip() or not units:
        return {"score": None, "grade": "보류", "unit_type": unit_type, "units": [],
                "review_suggestions": []}

    scored = [score_unit(answer_norm, u) for u in units]
    valid = [u["score"] for u in scored if u["score"] is not None]
    overall = round(sum(valid) / len(valid), 3) if valid else None
    grade = "보류" if overall is None else "O" if overall >= 0.8 else "△" if overall >= 0.5 else "X"

    sug = []
    for u in scored:
        for r in u["review_suggestions"]:
            if r not in sug:
                sug.append(r)
    if not sug and overall is not None:
        sug = ["stable"]

    return {"score": overall, "grade": grade, "unit_type": unit_type,
            "units": scored, "review_suggestions": sug}
