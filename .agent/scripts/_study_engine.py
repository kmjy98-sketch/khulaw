# -*- coding: utf-8 -*-
"""_study_engine.py — 적응형 학습 루프 엔진 파일럿 (쟁점 그래프 + 전파 활성화).

설계(사용자 확정 2026-06-23):
- 노드=쟁점, 엣지=연관쟁점(가중). 노드 강도=아는 정도(0~1).
- 틀리면 → 1-hop 연관쟁점 중 '약한 것'만 강화 큐에 추가(≤related_K). 맞으면 강도↑.
- baseline 큐로 범위 내 전 쟁점 ≥1회("한바퀴씩").
- ★ cutoff: 같은 쟁점 fails≥CUTOFF면 무한 드릴 중단하고 "이 파트 공부하라" 리턴(escalate).
- 채점: OX/Cloze=정확매칭(grade_objective), 사례=패널(외부 콜백, 파일럿은 주입).

순수 로직 — socratic-core/SRS/실 state 없이 검증. 실연동은 후속.
시스템 유틸리티(#30 면제).
"""


def grade_objective(given, correct):
    """OX/Cloze 정확매칭. 공백·대소문자·양끝 무시."""
    def norm(s):
        return "".join(str(s).split()).lower()
    return norm(given) == norm(correct)


class Node:
    __slots__ = ("strength", "attempts", "fails", "status", "source")

    def __init__(self, strength=0.3, source=""):
        self.strength = strength
        self.attempts = 0
        self.fails = 0
        self.status = "active"   # active | mastered | study
        self.source = source     # "이 파트 공부하라" 안내용(교재/wiki 위치)


class StudyEngine:
    def __init__(self, edges, sources=None, *, cutoff=3, mastery=0.8,
                 weak=0.5, related_k=3, up=0.34, down=0.2):
        # edges: {쟁점: [(연관쟁점, 가중0~1), ...]}
        self.edges = {k: list(v) for k, v in edges.items()}
        self.node = {k: Node(source=(sources or {}).get(k, k)) for k in edges}
        self.cfg = dict(cutoff=cutoff, mastery=mastery, weak=weak,
                        related_k=related_k, up=up, down=down)
        self.baseline_q = list(edges.keys())   # 한바퀴씩
        self.reinforce_q = []                   # 강화(우선)
        self.study_recs = []                    # 공부하라 권고
        self.trace = []

    def _active(self, n):
        return self.node[n].status == "active"

    def next_problem(self):
        """다음 출제 쟁점. 강화 우선 → baseline. 없으면 None."""
        for q in (self.reinforce_q, self.baseline_q):
            while q:
                n = q.pop(0)
                if self._active(n):
                    return n
        return None

    def submit(self, node, correct):
        """채점 결과 제출 → 상태 갱신 + 액션(강화/공부권고/마스터) 반환."""
        st = self.node[node]
        st.attempts += 1
        c = self.cfg
        if correct:
            st.strength = min(1.0, st.strength + c["up"])
            action = "none"
            if st.strength >= c["mastery"]:
                st.status = "mastered"
                action = "mastered"
            res = {"node": node, "result": "correct", "action": action, "strength": round(st.strength, 2)}
        else:
            st.fails += 1
            st.strength = max(0.0, st.strength - c["down"])
            if st.fails >= c["cutoff"]:
                st.status = "study"
                rec = {"node": node, "source": st.source, "fails": st.fails}
                self.study_recs.append(rec)
                res = {"node": node, "result": "wrong", "action": "study_recommend", "study": rec}
            else:
                # 전파 활성화: 약한 1-hop 연관쟁점만, 약할수록 우선, ≤related_k
                cand = [(n, w) for (n, w) in self.edges.get(node, [])
                        if self._active(n) and self.node[n].strength < c["weak"]]
                cand.sort(key=lambda x: x[1] * (1 - self.node[x[0]].strength), reverse=True)
                picked = [n for n, _ in cand[:c["related_k"]]]
                self.reinforce_q.extend(picked)
                self.reinforce_q.append(node)  # 본인 재드릴 → cutoff까지 "더 풀기"
                res = {"node": node, "result": "wrong", "action": "reinforce",
                       "targets": picked, "redrill": node}
        self.trace.append(res)
        return res

    def summary(self):
        return {
            "study_recommendations": self.study_recs,
            "mastered": [n for n, s in self.node.items() if s.status == "mastered"],
            "active_remaining": [n for n, s in self.node.items() if s.status == "active"],
            "nodes": {n: {"strength": round(s.strength, 2), "attempts": s.attempts,
                          "fails": s.fails, "status": s.status} for n, s in self.node.items()},
        }
