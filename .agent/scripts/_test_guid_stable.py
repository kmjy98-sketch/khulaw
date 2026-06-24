# -*- coding: utf-8 -*-
"""_test_guid_stable.py — _guid_stable.py 파일럿 검증 (#17 1청크 파일럿).

핵심 증명:
  - note_key는 카드 본문과 무관 → 본문 수정해도 guid 불변 → 재임포트 시 회독 보존.
  - 현 방식(legacy_seed, 내용 해시)은 같은 수정에 시드가 바뀜 → 버그 재현.
  - 출력 포맷이 card-wiki-pipeline §8.1의 `{stem}::{basic|cloze}::{seq:04d}`와 일치.
실행: python3 .agent/scripts/_test_guid_stable.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _guid_stable import guid_seed, note_key, extract_uid, legacy_seed  # noqa: E402

STEM = "논점민법재산법_p10-12"


class GuidStability(unittest.TestCase):
    def test_8_1_포맷_일치(self):
        # card-wiki-pipeline §8.1: {파일stem}::{basic|cloze}::{seq:04d}
        self.assertEqual(note_key(STEM, "cloze", 3), f"{STEM}::cloze::0003")
        self.assertEqual(note_key(STEM, "Basic", 42), f"{STEM}::basic::0042")

    def test_본문수정에도_시드불변(self):
        # 같은 (stem, 종류, 순번)이면 본문이 어떻든 시드 동일 → guid 불변
        self.assertEqual(guid_seed(STEM, "cloze", 3), guid_seed(STEM, "cloze", 3))

    def test_현재방식은_본문수정에_깨진다(self):
        # legacy(내용 해시): 한 단어만 더해도 시드가 달라짐 = 회독 유실 버그
        head = "### [요건] 채권자취소권"
        before = legacy_seed(STEM, head, "피보전채권 사해행위")
        after = legacy_seed(STEM, head, "피보전채권 사해행위 사해의사")
        self.assertNotEqual(before, after)

    def test_카드간_유일성(self):
        self.assertNotEqual(guid_seed(STEM, "cloze", 1), guid_seed(STEM, "cloze", 2))
        # 같은 블록의 Basic/Cloze 더블도 분리
        self.assertNotEqual(guid_seed(STEM, "cloze", 1), guid_seed(STEM, "basic", 1))
        # 파일이 다르면 같은 순번도 다른 카드
        self.assertNotEqual(guid_seed(STEM, "cloze", 1), guid_seed("작은변사기_p5", "cloze", 1))

    def test_explicit_uid는_재정렬에도_불변(self):
        # 카드가 밀려 순번이 5→9로 바뀌어도 uid 있으면 같은 노트
        self.assertEqual(
            guid_seed(STEM, "cloze", 5, explicit_uid="민총-0042"),
            guid_seed(STEM, "cloze", 9, explicit_uid="민총-0042"),
        )
        self.assertNotEqual(
            guid_seed(STEM, "cloze", 5, explicit_uid="민총-0042"),
            guid_seed(STEM, "cloze", 5, explicit_uid="민총-0043"),
        )
        # 같은 uid라도 basic/cloze 더블은 분리돼야 한다(블록당 2노트 충돌 방지)
        self.assertNotEqual(
            guid_seed(STEM, "cloze", 5, explicit_uid="민총-0042"),
            guid_seed(STEM, "basic", 5, explicit_uid="민총-0042"),
        )

    def test_explicit_key는_issue_id로_묶는다(self):
        # key 지정 시 file_stem 대신 issue_id로 note_key 구성(§8.1 key=issue_id)
        self.assertEqual(
            guid_seed(STEM, "cloze", 1, key="민법_채권자취소권"),
            "민법_채권자취소권::cloze::0001",
        )

    def test_uid_추출(self):
        self.assertEqual(
            extract_uid("### [요건] 룰\n<!-- uid: 민총-0042 -->\n앞: 내용"), "민총-0042"
        )
        self.assertEqual(extract_uid("**카드01**\nuid:: 형총-0007\n빈칸: ..."), "형총-0007")
        self.assertIsNone(extract_uid("### [요건] 룰\n앞: 내용\n뒤: 효과"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
