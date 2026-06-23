# -*- coding: utf-8 -*-
"""_test_guid_stable.py — _guid_stable.py 파일럿 검증 (#17 1청크 파일럿).

핵심 증명:
  - 카드 본문을 수정해도 새 시드가 기존과 동일 → GUID 불변 → 재임포트 시 회독 보존.
  - 현 방식(legacy_seed, 내용 해시)은 같은 수정에 시드가 바뀜 → 버그 재현.
실행: python3 .agent/scripts/_test_guid_stable.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _guid_stable import guid_seed, extract_uid, legacy_seed  # noqa: E402

SRC = "논점민법재산법_p10-12"


class GuidStability(unittest.TestCase):
    def test_본문수정에도_시드불변(self):
        # 같은 (출처, 순번, 종류)면 본문이 어떻든 시드 동일 → GUID 불변
        before = guid_seed(SRC, 3, "C")
        after = guid_seed(SRC, 3, "C")
        self.assertEqual(before, after)

    def test_현재방식은_본문수정에_깨진다(self):
        # legacy(내용 해시): 한 단어만 더해도 시드가 달라짐 = 회독 유실 버그
        head = "### [요건] 채권자취소권"
        before = legacy_seed(SRC, head, "피보전채권 사해행위")
        after = legacy_seed(SRC, head, "피보전채권 사해행위 사해의사")
        self.assertNotEqual(before, after)

    def test_카드간_유일성(self):
        # 순번이 다르면 다른 카드
        self.assertNotEqual(guid_seed(SRC, 1, "C"), guid_seed(SRC, 2, "C"))
        # 같은 블록의 Basic/Cloze 더블도 분리
        self.assertNotEqual(guid_seed(SRC, 1, "C"), guid_seed(SRC, 1, "B"))
        # 출처가 다르면 같은 순번도 다른 카드
        self.assertNotEqual(guid_seed(SRC, 1, "C"), guid_seed("작은변사기_p5", 1, "C"))

    def test_explicit_uid는_재정렬에도_불변(self):
        # 카드가 밀려 순번이 5→9로 바뀌어도 uid 있으면 같은 노트
        self.assertEqual(
            guid_seed(SRC, 5, "C", explicit_uid="민총-0042"),
            guid_seed(SRC, 9, "C", explicit_uid="민총-0042"),
        )
        # 서로 다른 uid는 서로 다른 카드
        self.assertNotEqual(
            guid_seed(SRC, 5, "C", explicit_uid="민총-0042"),
            guid_seed(SRC, 5, "C", explicit_uid="민총-0043"),
        )

    def test_uid_추출(self):
        self.assertEqual(
            extract_uid("### [요건] 룰\n<!-- uid: 민총-0042 -->\n앞: 내용"), "민총-0042"
        )
        self.assertEqual(extract_uid("**카드01**\nuid:: 형총-0007\n빈칸: ..."), "형총-0007")
        self.assertIsNone(extract_uid("### [요건] 룰\n앞: 내용\n뒤: 효과"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
