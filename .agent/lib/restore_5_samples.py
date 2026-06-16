#!/usr/bin/env python3
"""시범 5개 노트의 0. 소스 범위 표를 빈 상태로 초기화.

이후 link_*.py 스크립트들을 재실행하여 wikilink 재구성.
idempotent 마커를 피하기 위해 callout 전체 제거 + 빈 표 복원.
"""
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path('H:/내 드라이브/sync')

TARGETS = [
    ROOT / '민법' / '총칙' / '표현대리.md',
    ROOT / '민법' / '총칙' / '무권대리.md',
    ROOT / '민법' / '총칙' / '의사표시_통정허위표시.md',
    ROOT / '형법' / '총론' / '정당방위.md',
    ROOT / '헌법' / '총론' / '법치주의.md',
]

SOURCE_HEADER_PAT = re.compile(r'^##\s+0\.\s*(소스\s*범위|범위\s*전제)')


def reset_source_section(text: str) -> str:
    """0. 소스 범위 섹션을 헤더 + 빈 표로 초기화."""
    lines = text.split('\n')
    header_idx = None
    for i, line in enumerate(lines):
        if SOURCE_HEADER_PAT.match(line):
            header_idx = i
            break
    if header_idx is None:
        return text

    # 다음 ## 섹션 또는 --- 찾기
    end_idx = None
    for i in range(header_idx + 1, len(lines)):
        line = lines[i]
        if line.startswith('##') or (line.strip() == '---' and i > header_idx + 2):
            end_idx = i
            break
    if end_idx is None:
        end_idx = len(lines)

    # 빈 표로 교체
    new_section = [
        lines[header_idx],  # ## 0. 소스 범위
        '',
        '| 교재 | 범위 | 참조 |',
        '|------|------|------|',
        '',
    ]
    new_lines = lines[:header_idx] + new_section + lines[end_idx:]
    return '\n'.join(new_lines)


def main():
    for f in TARGETS:
        text = f.read_text(encoding='utf-8')
        new_text = reset_source_section(text)
        f.write_text(new_text, encoding='utf-8')
        print(f'  [RESET] {f.relative_to(ROOT)}')
    print(f'\n총 {len(TARGETS)}개 노트 초기화')


if __name__ == '__main__':
    main()
