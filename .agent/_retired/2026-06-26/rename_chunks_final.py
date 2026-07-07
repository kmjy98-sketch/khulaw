#!/usr/bin/env python3
"""최종 wikilink 갱신: chunk_rename_mapping_final.json 매핑을 정리노트에 일괄 적용."""
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
    for src in ['민법', '형법', '헌법']:
        for f in (ROOT / src).rglob('*.md'):
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
    print(f'처리 파일: {total_files}, 변경 파일: {changed_files}, 치환: {total_replacements}')


if __name__ == '__main__':
    main()
