#!/usr/bin/env python3
"""시범 5개 노트의 0. 소스 범위 표를 복구.

일반 link 스크립트는 "이미 참조된 청크"는 skip하므로 시범 5노트처럼
완전히 빈 상태에서 다른 노트들이 이미 참조하는 청크를 재매칭할 수 없음.
이 스크립트는 linked 필터 없이 5개 노트에 대해 전체 청크 매칭 → 교재별 행 생성.
"""
import sys
import re
import json
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path('H:/내 드라이브/sync')

# 기존 link_by_stem_tokens 모듈 import
sys.path.insert(0, str(Path('H:/내 드라이브/.agent/lib')))
import importlib.util
spec = importlib.util.spec_from_file_location('lbst', 'H:/내 드라이브/.agent/lib/link_by_stem_tokens.py')
lbst = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lbst)

TARGETS = [
    '표현대리',
    '무권대리',
    '의사표시_통정허위표시',
    '정당방위',
    '법치주의',
]


def find_textbook_label(chunk_path: Path) -> str:
    parts = chunk_path.parts
    try:
        idx = parts.index('_교재원문')
        return parts[idx + 2]
    except (ValueError, IndexError):
        return 'unknown'


def insert_source_rows(text: str, book_chunks: dict) -> str:
    """0. 소스 범위 표에 교재별 행 삽입. 빈 표를 기대."""
    lines = text.split('\n')
    header_idx = None
    for i, line in enumerate(lines):
        if re.match(r'^##\s+0\.\s*소스\s*범위', line):
            header_idx = i
            break
    if header_idx is None:
        return text

    # 헤더·구분자 찾기 (표 시작)
    table_header_idx = None
    for i in range(header_idx + 1, min(header_idx + 10, len(lines))):
        if lines[i].strip().startswith('| 교재'):
            table_header_idx = i
            break
    if table_header_idx is None:
        return text

    sep_idx = table_header_idx + 1  # 구분자

    # 새 행 추가 위치: 구분자 다음
    insert_pos = sep_idx + 1

    new_rows = []
    for book, chunks in book_chunks.items():
        if not chunks:
            continue
        links = ', '.join(f'[[{c}]]' for c in chunks)
        new_rows.append(f'| {book} | 본문/사례 | {links} |')

    new_lines = lines[:insert_pos] + new_rows + lines[insert_pos:]
    return '\n'.join(new_lines)


def main():
    notes = lbst.collect_notes()
    chunks = lbst.collect_chunks()

    for target_stem in TARGETS:
        if target_stem not in notes:
            print(f'  [NOT FOUND] {target_stem}')
            continue
        f, n_tokens = notes[target_stem]

        # 전체 청크 매칭 (linked 필터 없이)
        matches = []
        for c_stem, c_path, c_tokens in chunks:
            overlap = c_tokens & n_tokens
            if len(overlap) >= 1:
                matches.append((c_stem, c_path, len(overlap)))
        matches.sort(key=lambda x: -x[2])

        # 교재별로 그룹화 (책별 최대 8개)
        book_chunks = defaultdict(list)
        for c_stem, c_path, score in matches:
            book = find_textbook_label(c_path)
            if len(book_chunks[book]) < 8:
                book_chunks[book].append(c_stem)

        # 삽입
        text = f.read_text(encoding='utf-8')
        new_text = insert_source_rows(text, book_chunks)
        f.write_text(new_text, encoding='utf-8')

        total_wikis = sum(len(v) for v in book_chunks.values())
        print(f'  [OK] {target_stem}: {len(book_chunks)}개 교재, {total_wikis} wikilink')


if __name__ == '__main__':
    main()
