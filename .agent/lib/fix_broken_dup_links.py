#!/usr/bin/env python3
"""11-4 중복 청크 _trash 이동 후 깨진 wikilink 수정.

정책:
- 송영곤 사례연습2 `_교재판` / `_총론채총판`: 해당 wikilink 제거
  (원본인 suffix 없는 파일은 이미 있음)
- 박승수 `_2` / `_3`: 해당 wikilink 제거 또는 `_1`으로 교체
  (원본은 `_1`으로 남아있음)
"""
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path('H:/내 드라이브/sync')

# 존재하는 파일 stem
all_files = set(f.stem for f in ROOT.rglob('*.md'))

def fix_note(f: Path) -> tuple[int, int]:
    """노트에서 깨진 중복 wikilink 제거/교체."""
    text = f.read_text(encoding='utf-8')
    lines = text.split('\n')
    link_pat = re.compile(r'\[\[([^\]|#]+?)(?:\|[^\]]+)?(?:#[^\]]+)?\]\]')
    removed = 0
    replaced = 0

    for i, line in enumerate(lines):
        matches = list(link_pat.finditer(line))
        if not matches:
            continue

        # 각 link별 결정: 제거 or 교체
        ops = []  # (start, end, replacement)
        for m in matches:
            full = m.group(1).strip()
            if '/' in full:
                continue
            if full in all_files:
                continue  # 정상

            # 깨진 링크 — 패턴별 처리
            replacement = None
            # 1. 박승수 _2, _3 → _1로 교체 (원본 있는지 확인)
            m_bak = re.match(r'^(.+?)_([23])_(박승수_민법기본사례)$', full)
            if m_bak:
                base = m_bak.group(1)
                candidate = f'{base}_1_{m_bak.group(3)}'
                if candidate in all_files:
                    replacement = candidate
            # 2. 송영곤 사례연습2 _교재판/_총론채총판 → suffix 제거
            else:
                m_sol = re.match(r'^(.+?)(_송영곤_사례연습2)(_교재판|_총론채총판)$', full)
                if m_sol:
                    candidate = m_sol.group(1) + m_sol.group(2)
                    if candidate in all_files:
                        replacement = candidate

            ops.append((m.start(), m.end(), replacement, m.group(0)))

        if not ops:
            continue

        # 뒤에서부터 처리
        new_line = line
        for start, end, replacement, original in sorted(ops, key=lambda x: -x[0]):
            if replacement:
                # wikilink 내부 교체
                new_wikilink = f'[[{replacement}]]'
                new_line = new_line[:start] + new_wikilink + new_line[end:]
                replaced += 1
            else:
                # wikilink 통째 제거
                new_line = new_line[:start] + new_line[end:]
                removed += 1

        # 정리
        new_line = re.sub(r',\s*,', ',', new_line)
        new_line = re.sub(r'\|\s*,', '|', new_line)
        new_line = re.sub(r',\s*\|', ' |', new_line)
        new_line = re.sub(r'·\s*·', '·', new_line)
        lines[i] = new_line

    new_text = '\n'.join(lines)
    if new_text != text:
        f.write_text(new_text, encoding='utf-8')
    return removed, replaced


def main():
    total_removed = 0
    total_replaced = 0
    changed_files = 0
    # 정리노트
    for src in ['민법', '형법', '헌법']:
        for f in (ROOT / src).rglob('*.md'):
            if f.stem.startswith('_'):
                continue
            r, rep = fix_note(f, )
            if r > 0 or rep > 0:
                total_removed += r
                total_replaced += rep
                changed_files += 1
    # 교재목차 파일도 처리
    for f in (ROOT / '_교재원문').rglob('_교재목차.md'):
        r, rep = fix_note(f)
        if r > 0 or rep > 0:
            total_removed += r
            total_replaced += rep
            changed_files += 1
            print(f'  [교재목차] {f.relative_to(ROOT)}: 제거={r}, 교체={rep}')

    print(f'=== 요약 ===')
    print(f'  변경 파일: {changed_files}')
    print(f'  제거: {total_removed}')
    print(f'  교체: {total_replaced}')


if __name__ == '__main__':
    main()
