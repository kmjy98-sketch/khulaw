# -*- coding: utf-8 -*-
"""_test_study_engine.py — 적응형 학습 엔진 파일럿 검증. 실행: python3 이파일."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _study_engine import StudyEngine, grade_objective  # noqa: E402

EDGES = {
    "채권자취소권": [("사해행위", 0.9), ("수익자악의", 0.7), ("제척기간", 0.5)],
    "사해행위": [("무자력", 0.8)],
    "수익자악의": [], "제척기간": [], "무자력": [],
    "표현대리": [("기본대리권", 0.6)], "기본대리권": [],
}


def engine(**kw):
    e = StudyEngine(EDGES, **kw)
    return e


class StudyEngineTest(unittest.TestCase):
    def test_정확매칭_OX클로즈(self):
        self.assertTrue(grade_objective("O", " o "))
        self.assertTrue(grade_objective("무자력", "무자력"))
        self.assertFalse(grade_objective("X", "O"))
        self.assertFalse(grade_objective("선의", "악의"))

    def test_cutoff_공부권고(self):
        e = engine(cutoff=3)
        r1 = e.submit("제척기간", False)
        r2 = e.submit("제척기간", False)
        r3 = e.submit("제척기간", False)
        self.assertEqual(r1["action"], "reinforce")   # 1·2회는 강화 시도
        self.assertEqual(r3["action"], "study_recommend")
        self.assertEqual(e.node["제척기간"].status, "study")
        self.assertEqual(len(e.summary()["study_recommendations"]), 1)

    def test_전파_약한연관만(self):
        e = engine()
        e.node["사해행위"].strength = 0.9    # 강함 → 강화 제외
        e.node["수익자악의"].strength = 0.2  # 약함 → 강화 포함
        e.node["제척기간"].strength = 0.3   # 약함 → 포함
        r = e.submit("채권자취소권", False)
        self.assertEqual(r["action"], "reinforce")
        self.assertIn("수익자악의", r["targets"])
        self.assertIn("제척기간", r["targets"])
        self.assertNotIn("사해행위", r["targets"])  # 강한 노드는 강화 안 함

    def test_강화_상한(self):
        e = engine(related_k=1)
        for n in ("사해행위", "수익자악의", "제척기간"):
            e.node[n].strength = 0.1
        r = e.submit("채권자취소권", False)
        self.assertEqual(len(r["targets"]), 1)  # related_k=1 상한

    def test_강화_우선_출제(self):
        e = engine()
        e.node["무자력"].strength = 0.1
        e.submit("사해행위", False)              # 무자력 강화 큐 추가
        self.assertEqual(e.next_problem(), "무자력")  # baseline보다 강화 우선

    def test_baseline_한바퀴_및_마스터제외(self):
        e = engine(mastery=0.8, up=0.6)
        e.submit("표현대리", True)   # 0.3+0.6=0.9 → mastered
        self.assertEqual(e.node["표현대리"].status, "mastered")
        served = []
        while True:
            n = e.next_problem()
            if n is None:
                break
            served.append(n)
        self.assertNotIn("표현대리", served)        # 마스터는 재출제 안 함
        self.assertIn("채권자취소권", served)        # 나머지는 한바퀴
        self.assertEqual(len(set(served)), len(served))  # 중복 없음


if __name__ == "__main__":
    unittest.main(verbosity=2)
