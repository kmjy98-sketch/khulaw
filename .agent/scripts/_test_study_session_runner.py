# -*- coding: utf-8 -*-
"""_test_study_session_runner.py — 어댑터 검증. 실행: python3 이파일."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _study_session_runner import SessionRunner, Problem  # noqa: E402

GRAPH = {
    "채권자취소권": {"related": [("제척기간", 0.6)], "frequency": 10, "source": "채권자취소권"},
    "제척기간": {"related": [], "frequency": 5, "source": "《논점민법》 §406②"},
    "수익자악의": {"related": [], "frequency": 3, "source": "수익자악의"},
}
BANK = {
    "채권자취소권": Problem("채권자취소권", "case", "사안...", None),
    "제척기간": Problem("제척기간", "cloze", "제척기간은?", "1년"),
    "수익자악의": Problem("수익자악의", "ox", "...", "O"),
}


def provider(node):
    return BANK[node]


class RunnerTest(unittest.TestCase):
    def setUp(self):
        # 패널 stub: 채권자취소권 사례는 1회 오답(본인귀책 누락) 후 정답
        self.panel_calls = {"채권자취소권": [(False, [{"text": "본인귀책 누락", "review_type": "mini_application"}]),
                                          (True, [])]}

        def panel(problem, 답안):
            seq = self.panel_calls.get(problem.node, [])
            return seq.pop(0) if seq else (True, [])
        self.runner = SessionRunner(GRAPH, provider=provider, panel=panel, cutoff=3)

    def _drive(self, answers, max_steps=20):
        seqs = {k: list(v) for k, v in answers.items()}
        steps = 0
        while steps < max_steps:
            p = self.runner.next()
            if p is None:
                break
            steps += 1
            a = seqs[p.node].pop(0) if seqs.get(p.node) else ("" if p.ptype != "case" else "답안")
            self.runner.submit(p, a)
        return steps

    def test_사례는_패널로_라우팅(self):
        self.runner.submit(BANK["채권자취소권"], "내 답안")
        self.assertIn("mini_application", self.runner.weak_by_node["채권자취소권"])  # 패널 약점 기록

    def test_OX클로즈는_정확매칭(self):
        r1 = self.runner.submit(BANK["수익자악의"], " o ")   # 정규화 일치
        r2 = self.runner.submit(BANK["제척기간"], "30일")     # 불일치
        self.assertTrue(r1["correct"])
        self.assertFalse(r2["correct"])

    def test_cutoff_공부권고_및_SRS제안(self):
        self._drive({"제척기간": ["30일", "6개월", "3년"], "수익자악의": ["O"], "채권자취소권": ["a", "a"]})
        out = self.runner.finish()
        # 제척기간 3연속 오답 → 공부권고
        recs = [r["node"] for r in out["study_recommendations"]]
        self.assertIn("제척기간", recs)
        # SRS 제안: 제척기간은 study(+source), 채권자취소권은 review(mini_application)
        props = {p["node"]: p for p in out["srs_proposals"]}
        self.assertEqual(props["제척기간"]["kind"], "study")
        self.assertIn("§406", props["제척기간"]["source"])
        self.assertEqual(props["채권자취소권"]["review_type"], "mini_application")
        self.assertEqual(props["채권자취소권"]["초기_due"], "D+2")

    def test_정답은_SRS제안_없음(self):
        self.runner.submit(BANK["수익자악의"], "O")  # 정답
        out = self.runner.finish()
        self.assertNotIn("수익자악의", [p["node"] for p in out["srs_proposals"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
