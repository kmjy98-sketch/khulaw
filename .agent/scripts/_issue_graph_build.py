# -*- coding: utf-8 -*-
"""_issue_graph_build.py — 쟁점 그래프 생성기 파일럿 (5신호 병합).

볼트에 흩어진 연관쟁점 신호를 합쳐 엔진(_study_engine)이 먹는 가중 그래프로 만든다.
신호(실 데이터는 H:\·gitignore → 파일럿은 합성 입력으로 로직 검증):
  related   : discover_related_issues() 스코어 {쟁점:[(쟁점,score)]}  (회차·키워드·페이지)
  crossref  : 공통 판례 {사건번호:[쟁점...]}                          (같은 판례 인용=연관)
  연계      : 수동 연계 태그 {쟁점:[쟁점]}                            (최고 신뢰)
  cooccur   : 사안 공출현 {사안:[쟁점...]}                            (한 사안에 같이)
  backlinks : wiki 백링크 {쟁점:[쟁점]}
출력: {쟁점:{related:[(쟁점,weight0~1)], frequency, source}} — _study_engine의 EDGES/SOURCES 호환.
시스템 유틸리티(#30 면제).
"""
from collections import defaultdict
from itertools import combinations

# 신호별 가중(수동 연계 > 백링크 > 공통판례 ≈ discover > 공출현)
W = {"연계": 1.0, "backlink": 0.7, "crossref": 0.6, "related": 0.6, "cooccur": 0.5}


def build_graph(*, related=None, crossref=None, 연계=None, cooccur=None,
                backlinks=None, frequency=None, sources=None, subjects=None, weights=None):
    """subjects={쟁점:과목군}(민사/형사/공법) 주면 과목 다른 쟁점 간 엣지 차단(교차오염 방지)."""
    w = {**W, **(weights or {})}
    subj = subjects or {}
    acc = defaultdict(float)       # (a,b) 정렬키 → 누적 가중
    prov = defaultdict(set)        # 근거 신호 출처

    def add(a, b, weight, tag):
        if a == b or not a or not b:
            return
        # 과목 분리 원칙(#35): 민사·형사·공법 교차 엣지 금지(둘 다 과목 알 때만 차단)
        if subj.get(a) and subj.get(b) and subj[a] != subj[b]:
            return
        key = tuple(sorted((a, b)))
        acc[key] += weight
        prov[key].add(tag)

    for a, bs in (연계 or {}).items():
        for b in bs:
            add(a, b, w["연계"], "연계")
    for a, bs in (backlinks or {}).items():
        for b in bs:
            add(a, b, w["backlink"], "backlink")
    for _case, issues in (crossref or {}).items():
        for a, b in combinations(sorted(set(issues)), 2):
            add(a, b, w["crossref"], "crossref")
    for _사안, issues in (cooccur or {}).items():
        for a, b in combinations(sorted(set(issues)), 2):
            add(a, b, w["cooccur"], "cooccur")
    # discover 스코어는 신호 내에서 0~1 정규화 후 가중
    rel = related or {}
    rmax = max((s for lst in rel.values() for _, s in lst), default=1) or 1
    for a, lst in rel.items():
        for b, s in lst:
            add(a, b, w["related"] * (s / rmax), "related")

    if not acc:
        gmax = 1.0
    else:
        gmax = max(acc.values())

    # 노드 = 어디서든 언급된 전 쟁점(엣지가 차단돼 고립돼도 노드로 유지)
    nodes = set(frequency or {}) | set(sources or {}) | set(subj) | {x for k in acc for x in k}
    nodes |= set(rel) | {b for lst in rel.values() for b, _ in lst}
    for d in (연계 or {}, backlinks or {}):
        nodes |= set(d) | {b for bs in d.values() for b in bs}
    for d in (crossref or {}, cooccur or {}):
        nodes |= {x for issues in d.values() for x in issues}
    adj = defaultdict(list)
    for (a, b), v in acc.items():
        weight = round(v / gmax, 3)            # 0~1 정규화
        adj[a].append((b, weight))
        adj[b].append((a, weight))

    graph = {}
    for n in sorted(nodes):
        rels = sorted(adj.get(n, []), key=lambda x: x[1], reverse=True)
        graph[n] = {
            "related": rels,
            "frequency": (frequency or {}).get(n, 0),
            "source": (sources or {}).get(n, n),
        }
    return graph, {k: sorted(v) for k, v in prov.items()}


def to_engine_edges(graph):
    """_study_engine.StudyEngine(edges=...) 입력 형태로 변환."""
    return {n: d["related"] for n, d in graph.items()}


def to_engine_sources(graph):
    """StudyEngine(edges, sources=...) 의 sources 입력."""
    return {n: d["source"] for n, d in graph.items()}
