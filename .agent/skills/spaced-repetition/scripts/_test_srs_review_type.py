# -*- coding: utf-8 -*-
"""_test_srs_review_type.py — Q2-2 파일럿 검증. 실행: python3 이파일."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _srs_review_type import initial_due_offset, initial_next_review  # noqa: E402


class SrsReviewType(unittest.TestCase):
    def test_오프셋_표_일치(self):
        self.assertEqual(initial_due_offset("issue_spotting"), 1)
        self.assertEqual(initial_due_offset("conclusion_drill"), 1)
        self.assertEqual(initial_due_offset("keyword_recall"), 2)
        self.assertEqual(initial_due_offset("mini_application"), 2)
        self.assertEqual(initial_due_offset("outline_recall"), 3)
        self.assertEqual(initial_due_offset("stable"), 7)

    def test_미지정은_D플러스1(self):
        self.assertEqual(initial_due_offset("unknown_type"), 1)
        self.assertEqual(initial_due_offset(None), 1)

    def test_next_review_계산(self):
        # 등록일 고정 입력(Date.now 비의존) → 결정론적
        self.assertEqual(initial_next_review("2026-06-23", "keyword_recall"), "2026-06-25")
        self.assertEqual(initial_next_review("2026-06-23", "outline_recall"), "2026-06-26")
        self.assertEqual(initial_next_review("2026-06-30", "stable"), "2026-07-07")  # 월경계
        self.assertEqual(initial_next_review("2026-06-23", "issue_spotting"), "2026-06-24")


if __name__ == "__main__":
    unittest.main(verbosity=2)
