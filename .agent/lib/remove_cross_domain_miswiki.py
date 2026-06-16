#!/usr/bin/env python3
"""과목 간 오연결 wikilink 제거.

헌법 노트가 민법 교재청크를, 형법 노트가 민법 교재청크를 참조하는 등의
토큰 매칭 실수를 제거한다. 경로로 과목이 확정된 청크만 대상.
"""
import sys
import re
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path('H:/내 드라이브/sync')

# 교재원문 stem → 과목 매핑
chunk_subj = {}
for f in (ROOT / '_교재원문').rglob('*.md'):
    parts = f.relative_to(ROOT / '_교재원문').parts
    if len(parts) >= 2:
        chunk_subj[f.stem] = parts[0]  # 민법/형법/헌법/선택법


def fix_note(f: Path, src_subj: str) -> tuple[int, int]:
    """노트에서 다른 과목 청크 wikilink가 포함된 줄을 제거/정리.

    정책:
    1. 줄 전체가 표 행인 경우: 해당 wikilink만 제거
    2. 줄에 1개 wikilink만 있고 그것이 오연결: 줄 전체 삭제
    3. 줄에 여러 wikilink가 있고 일부만 오연결: 오연결 wikilink만 제거

    반환: (제거 wikilink 수, 변경 줄 수)
    """
    text = f.read_text(encoding='utf-8')
    lines = text.split('\n')
    link_pat = re.compile(r'\[\[([^\]|#]+?)(?:\|[^\]]+)?(?:#[^\]]+)?\]\]')
    removed_links = 0
    changed_lines = 0

    for i, line in enumerate(lines):
        matches = list(link_pat.finditer(line))
        if not matches:
            continue
        to_remove = []
        for m in matches:
            full = m.group(1).strip()
            if '/' in full:
                continue  # 경로 포함 링크는 건드리지 않음
            tgt = chunk_subj.get(full)
            if tgt and tgt != src_subj and tgt in ['민법', '형법', '헌법']:
                to_remove.append(m)
        if not to_remove:
            continue

        # wikilink 제거
        new_line = line
        for m in sorted(to_remove, key=lambda x: -x.start()):
            link_text = m.group(0)
            # 앞뒤의 ", " 또는 " · " 제거 시도
            new_line = new_line[:m.start()] + new_line[m.end():]
            removed_links += 1

        # 정리: 남은 ", ," / ", " 시작/끝 등 정리
        new_line = re.sub(r',\s*,', ',', new_line)
        new_line = re.sub(r'\|\s*,', '|', new_line)
        new_line = re.sub(r',\s*\|', ' |', new_line)
        new_line = re.sub(r'·\s*·', '·', new_line)

        if new_line != line:
            lines[i] = new_line
            changed_lines += 1

    new_text = '\n'.join(lines)
    if new_text != text:
        f.write_text(new_text, encoding='utf-8')
    return removed_links, changed_lines


def main():
    total_removed = 0
    total_changed = 0
    for src in ['민법', '형법', '헌법']:
        for f in (ROOT / src).rglob('*.md'):
            if f.stem.startswith('_'):
                continue
            r, c = fix_note(f, src)
            if r > 0:
                total_removed += r
                total_changed += c
                print(f'  [{src}] {f.stem}: 제거={r}, 변경줄={c}')

    print(f'\n=== 요약 ===')
    print(f'  제거된 wikilink: {total_removed}')
    print(f'  변경된 줄: {total_changed}')


if __name__ == '__main__':
    main()
