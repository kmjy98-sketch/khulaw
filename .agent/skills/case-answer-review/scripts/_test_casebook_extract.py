# -*- coding: utf-8 -*-
"""_test_casebook_extract.py — 추출기 회귀 방지(합성 입력). 실행: python3 이파일."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _casebook_extract import split_problems, extract_unit  # noqa: E402

MD = """# 사례 1 표현대리
甲과 乙은 A토지를 공유한다.
1. 丙은 A토지 소유권을 취득하는가? (15점)
## II. 丙에 대한 말소등기청구
민법 제214조에 기한 청구. <mark>[대리권남용]</mark> 쟁점.
판례(대판 1994.12.2, 93다1596) 참조.
# IV. 결 론
丙의 청구는 기각되어야 한다.
2. 손해배상을 청구할 수 있는가? (20점)
## II. 乙에 대한 청구
민법 제750조 불법행위. 결론은 인용한다.
"""


class CasebookExtract(unittest.TestCase):
    def test_설문_분할(self):
        ps = split_problems(MD)
        self.assertEqual(len(ps), 2)
        self.assertEqual(ps[0]["배점"], 15)
        self.assertEqual(ps[1]["배점"], 20)

    def test_근거조문_추출(self):
        u = extract_unit(split_problems(MD)[0])
        self.assertIn("§214", u["근거"])

    def test_결론_탐지(self):
        u0 = extract_unit(split_problems(MD)[0])
        u1 = extract_unit(split_problems(MD)[1])
        self.assertEqual(u0["결론"], "기각")
        self.assertEqual(u1["결론"], "인용")

    def test_쟁점_판례(self):
        u = extract_unit(split_problems(MD)[0])
        self.assertIn("대리권남용", u["쟁점"])
        self.assertTrue(any("93다1596" in k for k in u["keywords"]))

    def test_라벨_청구헤더(self):
        u = extract_unit(split_problems(MD)[0])
        self.assertIn("청구", u["label"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
