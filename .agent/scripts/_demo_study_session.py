# -*- coding: utf-8 -*-
"""_demo_study_session.py — 적응형 학습 세션 데모(합성).

OX/Cloze=정확매칭, 사례=패널(데모는 mock). 틀리면 약한 연관쟁점 강화,
일정 횟수 초과면 "이 파트 공부하라" 리턴. 실행: python3 이파일.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _study_engine import StudyEngine, grade_objective  # noqa: E402

EDGES = {
    "채권자취소권": [("사해행위", 0.9), ("수익자악의", 0.7), ("제척기간", 0.6)],
    "사해행위": [("무자력", 0.8)],
    "수익자악의": [], "제척기간": [], "무자력": [],
    "표현대리": [("기본대리권", 0.6)], "기본대리권": [],
}
SOURCES = {"제척기간": "《논점민법》 제406조 제2항 — 제척기간 단원"}

# 문제 은행: 사례=panel, ox/cloze=정확매칭
BANK = {
    "채권자취소권": ("case", None),
    "사해행위": ("case", None),
    "표현대리": ("case", None),
    "수익자악의": ("ox", "O"),
    "무자력": ("ox", "O"),
    "기본대리권": ("ox", "O"),
    "제척기간": ("cloze", "1년"),
}
# 학습자 시뮬레이션: 사례=패널결과(bool), ox/cloze=제출답안(str)
ANSWERS = {
    "채권자취소권": [False],            # 사례 틀림 → 약한 연관 강화
    "제척기간": ["30일", "6개월", "3년"],  # 클로즈 3연속 오답 → cutoff
    "수익자악의": ["O"], "무자력": ["O"], "기본대리권": ["O"],
    "사해행위": [True], "표현대리": [True],
}


def grade(node):
    ptype, ans = BANK[node]
    seq = ANSWERS.get(node, [])
    given = seq.pop(0) if seq else (True if ptype == "case" else ans)
    if ptype == "case":
        correct = bool(given)          # 패널(mock)
        how = f"패널={correct}"
    else:
        correct = grade_objective(given, ans)  # 정확매칭
        how = f"정확매칭 '{given}'=='{ans}'? {correct}"
    return ptype, correct, how


def main():
    e = StudyEngine(EDGES, SOURCES, cutoff=3, mastery=0.8, up=0.5)
    # 초기 강도: 일부 약하게
    for n, s in {"수익자악의": 0.2, "제척기간": 0.2, "사해행위": 0.4, "무자력": 0.3}.items():
        e.node[n].strength = s

    print("=== 적응형 학습 세션 (합성) ===\n")
    step = 0
    while step < 30:
        node = e.next_problem()
        if node is None:
            break
        step += 1
        ptype, correct, how = grade(node)
        r = e.submit(node, correct)
        tag = {"reinforce": f"→ 강화: {r.get('targets')}", "study_recommend": "→ ⚑ 공부하라 리턴",
               "mastered": "→ ★마스터", "none": ""}[r["action"]]
        src = ("  [" + e.node[node].source + "]") if r["action"] == "study_recommend" else ""
        print(f"{step:2d}. [{ptype:5s}] {node:8s} {('O' if correct else 'X')}  {how}  {tag}{src}")

    s = e.summary()
    print("\n--- 세션 요약 ---")
    print("⚑ 공부 권고:", [f"{r['node']}({r['source']})" for r in s["study_recommendations"]] or "없음")
    print("★ 마스터:", s["mastered"] or "없음")
    print("잔여 active:", s["active_remaining"] or "없음")


if __name__ == "__main__":
    main()
