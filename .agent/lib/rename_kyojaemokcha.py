#!/usr/bin/env python3
"""교재목차 wikilink 갱신: chunk_rename_mapping_final.json을 _교재목차.md에 적용."""
import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path('H:/내 드라이브/sync')

with open('.agent/state/chunk_rename_mapping_final.json', 'r', encoding='utf-8') as f:
    MAPPING = json.load(f)

print(f'매핑 수: {len(MAPPING)}')


def main():
    total_files = 0
    changed_files = 0
    total_replacements = 0
    for f in (ROOT / '_교재원문').rglob('_교재목차.md'):
        total_files += 1
        text = f.read_text(encoding='utf-8')
        new_text = text
        for old, new in MAPPING.items():
            if old in new_text:
                count = new_text.count(old)
                new_text = new_text.replace(old, new)
                total_replacements += count
        if new_text != text:
            f.write_text(new_text, encoding='utf-8')
            changed_files += 1
            rel = f.relative_to(ROOT)
            print(f'  [{rel}]')
    print(f'\n처리: {total_files}, 변경: {changed_files}, 치환: {total_replacements}')


if __name__ == '__main__':
    main()
