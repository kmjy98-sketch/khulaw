# -*- coding: utf-8 -*-
"""_demo_issue_graph.py — 쟁점 그래프 생성기 데모(합성). 실행: python3 이파일."""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 윈도우 cp949 콘솔 유니코드 출력 크래시 방지

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _issue_graph_build import build_graph, to_engine_edges, to_engine_sources  # noqa: E402
from _study_engine import StudyEngine  # noqa: E402

# 민사 클러스터 + 형사 1개. '횡령죄'와 '채권자취소권'이 같은 판례를 인용(교차 유혹)
SIGNALS = dict(
    related={"채권자취소권": [("사해행위", 8), ("수익자악의", 5), ("제척기간", 3)]},
    crossref={"2003다8862": ["채권자취소권", "수익자악의"],
              "공통사건": ["채권자취소권", "횡령죄"]},          # 민사↔형사 — 차단돼야
    연계={"채권자취소권": ["제척기간"]},
    cooccur={"사례1": ["채권자취소권", "사해행위", "수익자악의"]},
    backlinks={"채권자취소권": ["사해행위"]},
    frequency={"채권자취소권": 40, "사해행위": 35},
    sources={"제척기간": "《논점민법》 §406② 제척기간 단원"},
    subjects={"채권자취소권": "민사", "사해행위": "민사", "수익자악의": "민사",
              "제척기간": "민사", "횡령죄": "형사"},
)


def main():
    g, prov = build_graph(**SIGNALS)
    print("=== 쟁점 그래프(병합) ===")
    for n in g:
        if not g[n]["related"]:
            continue
        rels = ", ".join(f"{b}={w}({'+'.join(prov[tuple(sorted((n, b)))])})" for b, w in g[n]["related"])
        print(f"  {n} (빈도{g[n]['frequency']}) → {rels}")

    print("\n=== 과목 분리 확인 ===")
    cross = dict(g["채권자취소권"]["related"]).get("횡령죄")
    print(f"  채권자취소권(민사) ↔ 횡령죄(형사): {'차단됨 ✓' if cross is None else f'엣지 {cross} ✗누출'}")
    print(f"  공통 판례를 인용해도 과목 다르면 연결 안 됨")

    print("\n=== 엔진 연결 ===")
    e = StudyEngine(to_engine_edges(g), to_engine_sources(g))
    print(f"  StudyEngine 생성 OK · 첫 출제 후보: {e.next_problem()}")
    print(f"  제척기간 공부권고 위치: {e.node['제척기간'].source}")


if __name__ == "__main__":
    main()
