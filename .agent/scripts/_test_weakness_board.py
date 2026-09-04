# -*- coding: utf-8 -*-
"""_test_weakness_board.py — 약점보드 생성기 검증. 실행: python3 이파일."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _weakness_board import build_board  # noqa: E402

NODES = {
    "채권자취소권": {"strength": 0.3, "attempts": 2, "fails": 1, "status": "active"},
    "제척기간": {"strength": 0.1, "attempts": 3, "fails": 3, "status": "study"},
    "사기죄": {"strength": 0.4, "attempts": 1, "fails": 1, "status": "active"},
    "표현대리": {"strength": 0.9, "attempts": 1, "fails": 0, "status": "mastered"},
}
SUBJ = {"채권자취소권": "민사", "제척기간": "민사", "사기죄": "형사", "표현대리": "민사"}
STUDY = [{"node": "제척기간", "source": "《논점민법》 §406②", "fails": 3}]
PROPOSALS = [{"node": "채권자취소권", "초기_due": "D+2"}, {"node": "제척기간", "초기_due": "D+3"}]
COFAIL = {("채권자취소권", "사해행위"): 4}


class Board(unittest.TestCase):
    def setUp(self):
        self.md = build_board(nodes=NODES, study_recs=STUDY, srs_proposals=PROPOSALS,
                              subjects=SUBJ, cofail=COFAIL, date="2026-06-23")

    def test_집중학습_콜아웃_백링크(self):
        self.assertIn("[!warning]", self.md)
        self.assertIn("[[제척기간]]", self.md)        # 콜아웃엔 백링크 허용
        self.assertIn("《논점민법》 §406②", self.md)

    def test_과목별_섹션(self):
        self.assertIn("## 민사", self.md)
        self.assertIn("## 형사", self.md)

    def test_표셀_백링크금지(self):
        # 표 행(| 쟁점 |)에는 [[]] 없어야 함(#35)
        for line in self.md.splitlines():
            if line.startswith("| ") and "채권자취소권" in line and "강도" not in line:
                self.assertNotIn("[[", line)

    def test_마스터_제외(self):
        self.assertNotIn("표현대리", self.md)

    def test_복습due_표기(self):
        self.assertIn("D+3", self.md)  # 제척기간 due

    def test_클러스터_백링크(self):
        self.assertIn("[[채권자취소권]] ↔ [[사해행위]]", self.md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
