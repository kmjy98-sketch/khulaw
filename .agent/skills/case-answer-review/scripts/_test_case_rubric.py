# -*- coding: utf-8 -*-
"""_test_case_rubric.py — Q2-1 파일럿 검증. 실행: python3 이파일."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _case_rubric import score_rubric, score_rubric_units, score_unit, WEIGHTS  # noqa: E402


class CaseRubric(unittest.TestCase):
    def test_가중치_합_1(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0, places=6)

    def test_빈답안은_보류(self):
        r = score_rubric(answer_norm="")
        self.assertEqual(r["grade"], "보류")
        self.assertIsNone(r["score"])

    def test_근거없으면_전항목_보류(self):
        # 모든 기대입력 미제공 → 모든 항목 보류 → score None (source 없는 감점 금지 #1·#2)
        r = score_rubric(answer_norm="아무 답안 텍스트")
        self.assertEqual(r["grade"], "보류")
        self.assertTrue(all(v["status"] == "보류" for v in r["items"].values()))

    def test_보류항목_제외_재정규화(self):
        # 키워드만 근거 제공: 2/2 등장 → keyword 1.0. 나머지 보류 → score=1.0(재정규화)
        r = score_rubric(answer_norm="사해행위 피보전채권 모두 논했다",
                         required_keywords=["사해행위", "피보전채권"])
        self.assertEqual(r["items"]["keyword"]["status"], "채점")
        self.assertEqual(r["items"]["issue"]["status"], "보류")
        self.assertAlmostEqual(r["score"], 1.0, places=3)

    def test_결론_반대는_0(self):
        r = score_rubric(answer_norm="따라서 청구를 기각한다",
                         conclusion_patterns=["인용"],
                         opposite_conclusion_patterns=["기각"])
        self.assertEqual(r["items"]["conclusion"]["score"], 0.0)
        self.assertIn("conclusion_drill", r["review_suggestions"])

    def test_쟁점_별칭은_절반(self):
        # 명칭 누락, 별칭만 등장 → 0.5. (0.5는 <0.5 트리거에 안 걸림 → issue_spotting 미제안)
        r = score_rubric(answer_norm="채권자 취소 관련 논의",
                         expected_issues=[("채권자취소권", ["채권자 취소"])])
        self.assertEqual(r["items"]["issue"]["score"], 0.5)
        self.assertNotIn("issue_spotting", r["review_suggestions"])

    def test_쟁점_완전누락은_드릴제안(self):
        r = score_rubric(answer_norm="전혀 다른 내용",
                         expected_issues=["채권자취소권"])
        self.assertEqual(r["items"]["issue"]["score"], 0.0)
        self.assertIn("issue_spotting", r["review_suggestions"])

    def test_포섭_법리만이면_상한0_5(self):
        # 사실 0건 인용 + 법리(키워드) 있음 → 0.5 상한
        r = score_rubric(answer_norm="위험부담 법리를 서술",
                         required_keywords=["위험부담"],
                         application_facts=["매매목적물 멸실", "쌍무계약"])
        self.assertEqual(r["items"]["application"]["score"], 0.5)
        self.assertIn("mini_application", r["review_suggestions"])

    def test_우수답안은_O_stable(self):
        r = score_rubric(
            answer_norm="채권자취소권 쟁점. 사해행위 피보전채권 사해의사. 목차 서론 본론 결론. 따라서 인용한다. 매매목적물 멸실 쌍무계약 사실을 포섭",
            expected_issues=["채권자취소권"],
            required_keywords=["사해행위", "피보전채권", "사해의사"],
            answer_structure=["서론", "본론", "결론"],
            conclusion_patterns=["인용"],
            application_facts=["매매목적물 멸실", "쌍무계약"],
        )
        self.assertEqual(r["grade"], "O")
        self.assertEqual(r["review_suggestions"], ["stable"])
        self.assertTrue(all(v["status"] == "채점" for v in r["items"].values()))


class CaseRubricUnits(unittest.TestCase):
    # 민사 청구 단위 (민사사례연습1 구조: 청구→요건→쟁점→포섭→결론)
    MINSA_UNIT = {
        "label": "甲의 丙에 대한 말소등기청구",
        "근거": "§214",
        "요건": ["소유권 존재", "丙명의 등기"],
        "쟁점": ["대리권남용"],
        "포섭_사실": ["丙 악의", "저가매각"],
        "결론": "기각",
        "keywords": ["민법 제107조"],
    }

    def test_민사_우수답안_O(self):
        ans = ("甲의 丙에 대한 말소등기청구. 소유권 존재와 丙명의 등기를 요건으로 한다. "
               "쟁점은 대리권남용. 민법 제107조 단서 유추. 丙 악의로 저가매각 포섭. 따라서 기각")
        r = score_rubric_units(ans, [self.MINSA_UNIT], unit_type="청구")
        self.assertEqual(r["unit_type"], "청구")
        self.assertEqual(r["grade"], "O")
        self.assertEqual(r["review_suggestions"], ["stable"])

    def test_민사_결론반대_드릴(self):
        ans = ("甲의 丙에 대한 말소등기청구. 소유권 존재와 丙명의 등기. 대리권남용 쟁점. "
               "丙 악의 저가매각. 따라서 인용한다")  # 결론 반대(기각인데 인용)
        r = score_rubric_units(ans, [self.MINSA_UNIT], unit_type="청구")
        self.assertEqual(r["units"][0]["items"]["conclusion"]["score"], 0.0)
        self.assertIn("conclusion_drill", r["review_suggestions"])

    def test_형사_죄책_단위(self):
        unit = {
            "label": "사기죄",
            "근거": "§347",
            "요건": ["기망행위", "처분행위", "재산상 손해"],
            "쟁점": ["불법영득의사"],
            "포섭_사실": ["허위 고지", "송금"],
            "결론": "유죄",
        }
        ans = "사기죄. 기망행위 처분행위 재산상 손해. 불법영득의사 쟁점. 허위 고지로 송금 포섭. 유죄"
        r = score_rubric_units(ans, [unit], unit_type="죄책")
        self.assertEqual(r["unit_type"], "죄책")
        self.assertEqual(r["grade"], "O")

    def test_요건누락은_outline_제안(self):
        ans = "甲의 丙에 대한 말소등기청구. 대리권남용. 기각"  # 요건사실 열거 없음
        r = score_rubric_units(ans, [self.MINSA_UNIT], unit_type="청구")
        self.assertLess(r["units"][0]["items"]["structure"]["score"], 0.5)
        self.assertIn("outline_recall", r["review_suggestions"])

    def test_다단위_평균(self):
        u2 = dict(self.MINSA_UNIT, label="甲의 戊에 대한 부당이득청구", 결론="인용")
        ans = "甲의 丙에 대한 말소등기청구 기각, 甲의 戊에 대한 부당이득청구 인용"
        r = score_rubric_units(ans, [self.MINSA_UNIT, u2], unit_type="청구")
        self.assertEqual(len(r["units"]), 2)
        self.assertIsNotNone(r["score"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
