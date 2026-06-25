# -*- coding: utf-8 -*-
"""_study_session_runner.py — 적응형 학습 세션 어댑터 (엔진 ↔ 전달/채점/SRS).

엔진(_study_engine) + 그래프(_issue_graph_build)를 실 부품에 연결하는 접착제.
주입식 인터페이스(컨테이너는 stub, 실연동은 socratic-core/패널을 꽂음):
  provider(node) -> Problem(node, ptype, question, answer)   # ptype: ox|cloze|case
  panel(problem, 답안) -> (correct: bool, weaknesses: [{text, review_type}])  # 사례 전용
채점 분기: OX/Cloze=grade_objective(정확매칭), 사례=panel.
finish() = 공부권고 + SRS 제안(검토용). silent write 금지(#16) — 제안만, 기록은 사용자 확정.
시스템 유틸리티(#30 면제).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _study_engine import StudyEngine, grade_objective  # noqa: E402
from _issue_graph_build import to_engine_edges, to_engine_sources  # noqa: E402

_SR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "spaced-repetition", "scripts")
sys.path.insert(0, _SR)
from _srs_review_type import initial_due_offset  # noqa: E402


class Problem:
    __slots__ = ("node", "ptype", "question", "answer")

    def __init__(self, node, ptype, question="", answer=None):
        self.node, self.ptype, self.question, self.answer = node, ptype, question, answer


class SessionRunner:
    def __init__(self, graph, *, provider, panel=None, strengths=None, **engine_kw):
        self.engine = StudyEngine(to_engine_edges(graph), to_engine_sources(graph), **engine_kw)
        for n, s in (strengths or {}).items():
            if n in self.engine.node:
                self.engine.node[n].strength = s
        self.provider = provider
        self.panel = panel
        self.weak_by_node = {}  # node -> [review_type...] (SRS 제안용)

    def next(self):
        """다음 출제 Problem(없으면 None). 엔진이 쟁점 선택 → provider가 문제 공급."""
        node = self.engine.next_problem()
        return None if node is None else self.provider(node)

    def submit(self, problem, 답안):
        """채점(분기) → 엔진 갱신 → 결과."""
        if problem.ptype == "case":
            if self.panel:
                correct, weaknesses = self.panel(problem, 답안)
            else:
                correct, weaknesses = grade_objective(답안, problem.answer), []
        else:  # ox / cloze
            correct = grade_objective(답안, problem.answer)
            weaknesses = [] if correct else [{"text": f"{problem.node} {problem.ptype} 오답",
                                              "review_type": "keyword_recall"}]
        for wk in weaknesses:
            self.weak_by_node.setdefault(problem.node, []).append(wk.get("review_type", "keyword_recall"))
        res = self.engine.submit(problem.node, correct)
        return {**res, "correct": correct, "weaknesses": weaknesses}

    def finish(self):
        """세션 종료 → 공부권고 + SRS 제안(검토용). 기록은 사용자 확정 시."""
        proposals = []
        for n, st in self.engine.node.items():
            if st.status == "study":
                rt = "outline_recall"
                proposals.append({"node": n, "kind": "study", "source": st.source,
                                  "review_type": rt, "초기_due": f"D+{initial_due_offset(rt)}"})
            elif st.fails > 0 and st.status != "mastered":
                rt = (self.weak_by_node.get(n) or ["keyword_recall"])[0]
                proposals.append({"node": n, "kind": "review", "review_type": rt,
                                  "초기_due": f"D+{initial_due_offset(rt)}"})
        return {"study_recommendations": self.engine.study_recs,
                "srs_proposals": proposals, "summary": self.engine.summary()}
