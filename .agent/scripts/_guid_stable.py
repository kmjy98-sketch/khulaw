# -*- coding: utf-8 -*-
"""_guid_stable.py — build_v37_apkg.py용 안정 GUID 시드 (파일럿).

배경: card-wiki-pipeline.md §8.1 / anki-card-generation §171은 빌더가 genanki guid를
안정 note_key 기반 `{파일stem}::{basic|cloze}::{seq:04d}`로 만들어 "카드 텍스트를
수정해도 guid 유지 → 재임포트 시 복습이력 보존"한다고 명시(2026-06-16 전환·검증 완료로 문서화).
그러나 실제 build_v37_apkg.py(184·199행)는 여전히
`genanki.guid_for(src, blk[:30], 정규화본문)` — 즉 **내용 해시**다. 본문을 한 글자만
고쳐도 guid가 바뀌어 재임포트 시 새 카드 생성·기존 카드 고아화(회독 유실).

이 모듈은 §8.1 문서 스펙을 코드로 구현한다. 내용이 아니라 정체성(note_key)에 guid를 묶는다.
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


def note_key(file_stem, card_type, seq, key=None):
    """§8.1 안정 note_key: `{key}::{card_type}::{seq:04d}`.

    file_stem : 카드 소스 파일 stem(예: '논점민법재산법_p10-12'). key 미지정 시 이게 key.
    card_type : 'basic' | 'cloze'.
    seq       : 같은 파일 안에서의 카드 순번(정수). 본문 수정에 불변.
    key       : issue_id 또는 {출처약어}_{소제목} 등 명시 키(있으면 file_stem 대신 사용).
    """
    base = str(key or file_stem).strip()
    ct = str(card_type).strip().lower()
    return f"{base}::{ct}::{int(seq):04d}"


def guid_seed(file_stem, card_type, seq, key=None, explicit_uid=None):
    """genanki.guid_for에 넘길 단일 문자열. 본문 내용 비의존 → 수정해도 guid 유지.

    explicit_uid 있으면 그 값으로 고정(카드 삽입·재정렬에도 불변). 없으면 §8.1 note_key.
    호출부 예: g = genanki.guid_for(guid_seed(stem, "cloze", seq, explicit_uid=extract_uid(blk)))
    """
    if explicit_uid:
        return str(explicit_uid).strip()
    return note_key(file_stem, card_type, seq, key=key)


def legacy_seed(src, block_head, normalized_content):
    """현 build_v37_apkg.py가 쓰는 '내용 해시' 시드(대조용). 본문이 바뀌면 시드도 바뀐다."""
    return (src, block_head[:30], re.sub(r"\s+", "", normalized_content))
