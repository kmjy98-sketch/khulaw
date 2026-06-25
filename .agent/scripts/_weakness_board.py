# -*- coding: utf-8 -*-
"""_weakness_board.py — 약점보드 생성기 (옵시디언 대시보드).

적응형 엔진/runner 출력 + 상태를 받아 과목별 약점 보드(마크다운)를 만든다.
- 집중학습(공부권고)·복습 due·약한 클러스터(co-failure)를 한 화면에.
- 백링크 규칙(#35): 표 셀에는 [[]] 금지, 콜아웃·리스트에는 허용.
- 과목 분리(#35): 과목별 섹션으로 분리.
시스템 유틸리티(#30 면제).
"""

_ORDER = ["민사", "형사", "공법", "선택", "기타"]


def build_board(*, nodes, study_recs=None, srs_proposals=None, subjects=None,
                cofail=None, date="YYYY-MM-DD", subject_order=None):
    """nodes: {쟁점:{strength,attempts,fails,status}} (engine.summary()['nodes']).
    srs_proposals: [{node, 초기_due, ...}]. cofail: {(a,b):count}."""
    subj = subjects or {}
    due_of = {p["node"]: p.get("초기_due", "") for p in (srs_proposals or [])}
    L = ["---", "type: 약점보드", f"생성: {date}", "---", "", f"# 약점보드 ({date})", ""]

    # 1) 집중 학습(공부권고) — 콜아웃, 백링크 허용
    if study_recs:
        L.append("> [!warning] 집중 학습 필요 (반복 오답 → 교재 복귀)")
        for r in study_recs:
            L.append(f"> - [[{r['node']}]] — {r.get('source', '')} ({r.get('fails', '?')}회 오답)")
        L.append("")

    # 2) 과목별 약점 표 — 표 셀엔 백링크 금지(#35), 평문
    by = {}
    for n, st in nodes.items():
        if st.get("status") == "mastered":
            continue
        by.setdefault(subj.get(n, "기타"), []).append((n, st))
    order = subject_order or _ORDER
    for s in order + [k for k in sorted(by) if k not in order]:
        if s not in by:
            continue
        L.append(f"## {s}")
        L.append("| 쟁점 | 강도 | 상태 | 오답 | 복습 |")
        L.append("|---|---:|---|---:|---|")
        for n, st in sorted(by[s], key=lambda x: x[1].get("strength", 0)):
            L.append(f"| {n} | {st.get('strength', 0)} | {st.get('status', '')} "
                     f"| {st.get('fails', 0)} | {due_of.get(n, '—')} |")
        L.append("")

    # 3) 자주 함께 틀리는 클러스터 — 리스트, 백링크 허용
    if cofail:
        top = sorted(cofail.items(), key=lambda x: -x[1])[:10]
        if top:
            L.append("## 자주 함께 틀리는 클러스터 (co-failure)")
            for (a, b), c in top:
                L.append(f"- [[{a}]] ↔ [[{b}]] ({c}회)")
            L.append("")

    return "\n".join(L).rstrip() + "\n"
