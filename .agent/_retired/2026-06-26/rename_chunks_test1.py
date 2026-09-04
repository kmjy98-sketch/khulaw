#!/usr/bin/env python3
"""시범 1: 송영곤_사례 5청크 wikilink 일괄 갱신.

매핑:
  송영곤_사례_ch01_p0001-0030 → 권리주체사례_송영곤_사례
  송영곤_사례_ch02_p0031-0060 → 대리사례1_송영곤_사례
  송영곤_사례_ch03_p0061-0090 → 대리사례2_송영곤_사례
  송영곤_사례_ch04_p0091-0120 → 소멸시효사례1_송영곤_사례
  송영곤_사례_ch05_p0121-0153 → 소멸시효사례2_송영곤_사례
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브/sync')

MAPPING = {
    '송영곤_사례_ch01_p0001-0030': '권리주체사례_송영곤_사례',
    '송영곤_사례_ch02_p0031-0060': '대리사례1_송영곤_사례',
    '송영곤_사례_ch03_p0061-0090': '대리사례2_송영곤_사례',
    '송영곤_사례_ch04_p0091-0120': '소멸시효사례1_송영곤_사례',
    '송영곤_사례_ch05_p0121-0153': '소멸시효사례2_송영곤_사례',
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
                rel = f.relative_to(ROOT)
                print(f'  [{rel}]')

    print(f'\n=== 요약 ===')
    print(f'  처리 파일: {total_files}')
    print(f'  변경 파일: {changed_files}')
    print(f'  총 치환 수: {total_replacements}')


if __name__ == '__main__':
    main()
