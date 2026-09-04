# -*- coding: utf-8 -*-
"""_reinforce_learn.py — 강화 학습 레이어: co-failure 기반 쟁점 엣지 학습.

정적 그래프(_issue_graph_build)는 '일반적' 연관을 준다. 여기에 학습자 세션 이력의
'함께 틀린'(co-failure) 신호를 얹어, 그 사람이 실제로 혼동하는 쟁점쌍 엣지를 강화한다
(헤비안식: 같이 틀리면 연결 강화 = "신경망이 학습자에 맞춰 학습").
과목 분리(#35) 유지 — 민/형/공 교차는 강화·생성 안 함.
시스템 유틸리티(#30 면제).
"""
import copy
from collections import defaultdict
from itertools import combinations


def accumulate_cofail(sessions):
    """sessions: [[같은 세션에서 틀린 쟁점들], ...] → {(a,b 정렬): 공동오답 횟수}."""
    cf = defaultdict(int)
    for failed in sessions:
        for a, b in combinations(sorted(set(failed)), 2):
            cf[(a, b)] += 1
    return dict(cf)


def reinforce_edges(graph, cofail, *, subjects=None, beta=0.3, create_threshold=None):
    """co-fail로 엣지 강화. 기존 엣지는 부스트, create_threshold 이상이면 신규(같은 과목).
    과목 다른 쌍은 무시(#35). 원본 불변, 새 그래프 반환."""
    subj = subjects or {}
    cfmax = max(cofail.values(), default=1) or 1
    g = copy.deepcopy(graph)
    adj = {n: dict(d.get("related", [])) for n, d in g.items()}

    for (a, b), c in cofail.items():
        if subj.get(a) and subj.get(b) and subj[a] != subj[b]:
            continue  # 과목 분리
        if a not in adj or b not in adj:
            continue
        boost = beta * (c / cfmax)
        if b in adj[a]:                                   # 기존 엣지 부스트
            for x, y in ((a, b), (b, a)):
                adj[x][y] = round(min(1.0, adj[x][y] + boost), 3)
        elif create_threshold and c >= create_threshold:  # 신규 엣지(같은 과목)
            adj[a][b] = adj[b][a] = round(min(1.0, boost), 3)

    for n in g:
        g[n]["related"] = sorted(adj.get(n, {}).items(), key=lambda x: x[1], reverse=True)
    return g
