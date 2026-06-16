#!/usr/bin/env python3
"""시범 2: 송영곤_요건사실론 7청크 wikilink 일괄 갱신."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path('H:/내 드라이브/sync')

MAPPING = {
    '송영곤_요건사실론_ch01_p0001-0030': '청구취지작성법1_송영곤_요건사실론',
    '송영곤_요건사실론_ch02_p0031-0060': '청구취지작성법2_송영곤_요건사실론',
    '송영곤_요건사실론_ch03_p0061-0090': '청구원인_송영곤_요건사실론',
    '송영곤_요건사실론_ch04_p0091-0120': '항변재항변1_송영곤_요건사실론',
    '송영곤_요건사실론_ch05_p0121-0150': '항변재항변2_송영곤_요건사실론',
    '송영곤_요건사실론_ch06_p0151-0180': '청구별요건사실_송영곤_요건사실론',
    '송영곤_요건사실론_ch07_p0181-0183': '요건사실종합_송영곤_요건사실론',
}

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
