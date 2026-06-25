# -*- coding: utf-8 -*-
"""_test_issue_graph.py — 쟁점 그래프 생성기 검증. 실행: python3 이파일."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _issue_graph_build import build_graph, to_engine_edges, to_engine_sources  # noqa: E402
from _study_engine import StudyEngine  # noqa: E402


def w(graph, a, b):
    if a not in graph:
        return None
    return dict(graph[a]["related"]).get(b)


class IssueGraph(unittest.TestCase):
    def test_공통판례_엣지생성(self):
        g, prov = build_graph(crossref={"2003다8862": ["채권자취소권", "수익자악의"]})
        self.assertIsNotNone(w(g, "채권자취소권", "수익자악의"))
        self.assertIn("crossref", prov[("수익자악의", "채권자취소권")])

    def test_대칭(self):
        g, _ = build_graph(backlinks={"A": ["B"]})
        self.assertEqual(w(g, "A", "B"), w(g, "B", "A"))

    def test_연계가_단일신호중_최고(self):
        g, _ = build_graph(연계={"A": ["B"]}, crossref={"c": ["C", "D"]})
        self.assertGreater(w(g, "A", "B"), w(g, "C", "D"))  # 연계 1.0 > crossref 0.6

    def test_다신호_누적(self):
        # (E,F)=backlink0.7+cooccur0.5 vs (C,D)=crossref0.6
        g, prov = build_graph(backlinks={"E": ["F"]}, cooccur={"s": ["E", "F"]},
                              crossref={"c": ["C", "D"]})
        self.assertGreater(w(g, "E", "F"), w(g, "C", "D"))
        self.assertEqual(prov[("E", "F")], ["backlink", "cooccur"])  # 근거 2신호

    def test_정규화_0_1(self):
        g, _ = build_graph(연계={"A": ["B"]}, backlinks={"E": ["F"]}, cooccur={"s": ["E", "F"]})
        vals = [v for n in g for _, v in g[n]["related"]]
        self.assertTrue(all(0 <= v <= 1 for v in vals))
        self.assertAlmostEqual(max(vals), 1.0)  # 최대 엣지 = 1.0

    def test_엔진_호환(self):
        g, _ = build_graph(
            related={"채권자취소권": [("사해행위", 8), ("수익자악의", 5)]},
            연계={"채권자취소권": ["제척기간"]},
            frequency={"채권자취소권": 40}, sources={"제척기간": "《논점민법》 §406②"})
        e = StudyEngine(to_engine_edges(g), to_engine_sources(g))  # 엔진이 그대로 소비
        self.assertEqual(e.node["제척기간"].source, "《논점민법》 §406②")
        self.assertIsNotNone(e.next_problem())

    def test_빈입력_안전(self):
        g, prov = build_graph()
        self.assertEqual(g, {})

    def test_과목분리_교차차단(self):
        # 민법 쟁점과 형법 쟁점이 같은 판례/키워드로 엮여도 교차 엣지 금지
        g, _ = build_graph(
            crossref={"같은사건번호": ["사기죄", "착오"]},   # 형법 vs 민법
            연계={"착오": ["취소"]},                       # 둘 다 민법 → 허용
            subjects={"사기죄": "형사", "착오": "민사", "취소": "민사"})
        self.assertIsNone(w(g, "사기죄", "착오"))   # 형사↔민사 차단
        self.assertIsNotNone(w(g, "착오", "취소"))  # 민사 내 유지

    def test_과목미상은_유지(self):
        # 한쪽이라도 과목 모르면 판단 불가 → 유지(보수적)
        g, _ = build_graph(연계={"A": ["B"]}, subjects={"A": "민사"})
        self.assertIsNotNone(w(g, "A", "B"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
