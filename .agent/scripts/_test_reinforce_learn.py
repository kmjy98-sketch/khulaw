# -*- coding: utf-8 -*-
"""_test_reinforce_learn.py — 강화학습 레이어 검증. 실행: python3 이파일."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _reinforce_learn import accumulate_cofail, reinforce_edges  # noqa: E402

GRAPH = {
    "채권자취소권": {"related": [("사해행위", 0.5)], "frequency": 0, "source": "채권자취소권"},
    "사해행위": {"related": [("채권자취소권", 0.5)], "frequency": 0, "source": "사해행위"},
    "수익자악의": {"related": [], "frequency": 0, "source": "수익자악의"},
    "사기죄": {"related": [], "frequency": 0, "source": "사기죄"},
}
SUBJ = {"채권자취소권": "민사", "사해행위": "민사", "수익자악의": "민사", "사기죄": "형사"}


def w(g, a, b):
    return dict(g[a]["related"]).get(b)


class Reinforce(unittest.TestCase):
    def test_cofail_누적(self):
        cf = accumulate_cofail([["A", "B"], ["A", "B", "C"]])
        self.assertEqual(cf[("A", "B")], 2)
        self.assertEqual(cf[("A", "C")], 1)

    def test_기존엣지_부스트(self):
        cf = {("사해행위", "채권자취소권"): 5}
        g = reinforce_edges(GRAPH, cf, subjects=SUBJ, beta=0.3)
        self.assertGreater(w(g, "채권자취소권", "사해행위"), 0.5)   # 0.5 → 0.8
        self.assertEqual(w(g, "채권자취소권", "사해행위"), w(g, "사해행위", "채권자취소권"))  # 대칭

    def test_과목교차_무시(self):
        cf = {("사기죄", "채권자취소권"): 9}  # 형사↔민사
        g = reinforce_edges(GRAPH, cf, subjects=SUBJ, beta=0.3, create_threshold=1)
        self.assertIsNone(w(g, "사기죄", "채권자취소권"))  # 신규 생성 안 됨

    def test_같은과목_신규엣지(self):
        cf = {("채권자취소권", "수익자악의"): 4}  # 둘 다 민사, 엣지 없음
        g = reinforce_edges(GRAPH, cf, subjects=SUBJ, beta=0.3, create_threshold=3)
        self.assertIsNotNone(w(g, "채권자취소권", "수익자악의"))  # 임계 넘어 생성

    def test_원본불변(self):
        before = dict(GRAPH["채권자취소권"]["related"])
        reinforce_edges(GRAPH, {("사해행위", "채권자취소권"): 5}, subjects=SUBJ)
        self.assertEqual(dict(GRAPH["채권자취소권"]["related"]), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
