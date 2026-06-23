# -*- coding: utf-8 -*-
"""_guid_stable.py — build_v37_apkg.py용 안정 GUID 시드 전략 (파일럿).

배경: 현 build_v37_apkg.py는 genanki.guid_for(src, blk[:30], 정규화본문)으로
GUID를 만든다. GUID가 '본문 내용'에 묶여 있어, 카드 텍스트를 한 글자라도
수정하면 GUID가 바뀌고 → 재임포트 시 새 카드 생성 + 기존 카드 고아화(회독 유실).
오타/OCR 교정이 잦은 운영에서 치명적.

해결: GUID 시드를 '내용'이 아니라 '정체성'에 묶는다.
  1) explicit_uid 있으면 그것만 사용  → 삽입·재정렬에도 불변 (가장 강함)
  2) 없으면 (출처, 파일내 순번, 카드종류) 위치 기반 → 본문 in-place 수정에 불변
     (한계: 카드 삽입/삭제/재정렬 시 순번이 밀린다. 그 경우만 explicit uid 부여로 고정)

genanki README 권고("정체성에 해당하는 필드만 해시하라")와 정합.
시스템 유틸리티 — 근거 2줄 규칙(#30) 면제.
"""
import re

# explicit uid 표기 흡수: `<!-- uid: 민총-0042 -->` 또는 `uid:: 민총-0042` / `uid: 민총-0042`
_UID_RE = re.compile(
    r"<!--\s*uid\s*:\s*([^\s>]+)\s*-->|^\s*uid\s*::?\s*(\S+)", re.MULTILINE
)


def extract_uid(block):
    """카드 블록에서 영속 uid를 추출. 없으면 None."""
    if not block:
        return None
    m = _UID_RE.search(block)
    if not m:
        return None
    return (m.group(1) or m.group(2) or "").strip() or None


def guid_seed(src, card_index, kind, explicit_uid=None):
    """안정 GUID 시드(튜플)를 반환. 호출부: genanki.guid_for(*guid_seed(...)).

    src           : 출처 정규화 문자열 (예: '논점민법재산법_p10-12')
    card_index    : 같은 출처 파일 안에서의 카드 순번(정수, 0부터). 본문 수정에 불변.
    kind          : 'B'(Basic) | 'C'(Cloze) — 한 블록이 둘 다 낳을 때 충돌 방지.
    explicit_uid  : 있으면 위치와 무관하게 이 값으로 고정(삽입/재정렬 안전).
    """
    if explicit_uid:
        return ("v37uid", str(explicit_uid).strip(), kind)
    return ("v37ord", str(src), int(card_index), kind)


def legacy_seed(src, block_head, normalized_content):
    """현 build_v37_apkg.py가 쓰는 '내용 해시' 시드(대조용). 본문이 바뀌면 시드도 바뀐다."""
    return (src, block_head[:30], re.sub(r"\s+", "", normalized_content))
