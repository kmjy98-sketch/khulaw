#!/usr/bin/env python3
"""0. 소스 범위 표를 Obsidian callout 안으로 감싸서 접기.

입력: 정리노트 파일
출력: 표가 `> [!note]-` callout 안으로 들어감 (기본 접힌 상태)

idempotent: 이미 callout 안에 있으면 건너뜀
"""
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path('H:/내 드라이브/sync')

SOURCE_HEADER_PAT = re.compile(r'^##\s+0\.\s*(소스\s*범위|범위\s*전제)', re.MULTILINE)


def collapse_source_table(text: str) -> tuple[str, bool]:
    """0. 소스 범위 표를 callout으로 감싸기."""
    lines = text.split('\n')
    header_idx = None
    for i, line in enumerate(lines):
        if SOURCE_HEADER_PAT.match(line):
            header_idx = i
            break
    if header_idx is None:
        return text, False

    # 이미 callout 안인지 확인
    if header_idx + 1 < len(lines) and lines[header_idx + 1].strip().startswith('>'):
        return text, False

    # 표 시작·끝 찾기
    table_start = None
    table_end = None
    for i in range(header_idx + 1, len(lines)):
        line = lines[i]
        if line.strip().startswith('|'):
            if table_start is None:
                table_start = i
            table_end = i
        elif table_start is not None:
            break
        elif line.startswith('##') or line.startswith('---'):
            break

    if table_start is None or table_end is None:
        return text, False

    # wikilink 수 계산
    wiki_count = 0
    row_count = 0
    for i in range(table_start, table_end + 1):
        wiki_count += lines[i].count('[[')
        row_count += 1
    # 헤더·구분자 제외
    row_count = max(0, row_count - 2)

    # 표 줄들을 callout 안으로 변환
    new_lines = lines[:header_idx + 1]
    new_lines.append('')
    new_lines.append(f'> [!note]- 📚 교재 참조 ({row_count}개 교재, {wiki_count}+ 청크)')
    # 표 행들 앞에 `> ` 추가
    for i in range(table_start, table_end + 1):
        new_lines.append('> ' + lines[i])
    # 표 전 빈 줄 있으면 건너뜀
    # 표 뒤 이어가기
    new_lines.extend(lines[table_end + 1:])

    # 빈 줄 정리: callout 이후에 빈 줄 1개만 보장
    return '\n'.join(new_lines), True


def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    args = [a for a in args if a != '--dry-run']

    # 대상 파일
    if args:
        targets = [Path(a) for a in args]
    else:
        # 시범 5개
        targets = [
            ROOT / '민법' / '총칙' / '표현대리.md',
            ROOT / '민법' / '총칙' / '무권대리.md',
            ROOT / '민법' / '총칙' / '의사표시_통정허위표시.md',
            ROOT / '형법' / '총론' / '정당방위.md',
            ROOT / '헌법' / '총론' / '법치주의.md',
        ]

    total = 0
    changed = 0
    for f in targets:
        if not f.exists():
            print(f'  [NOT FOUND] {f}')
            continue
        total += 1
        text = f.read_text(encoding='utf-8')
        new_text, modified = collapse_source_table(text)
        if modified:
            if not dry_run:
                f.write_text(new_text, encoding='utf-8')
            changed += 1
            rel = f.relative_to(ROOT) if str(f).startswith(str(ROOT)) else f
            print(f'  [OK] {rel}')
        else:
            rel = f.relative_to(ROOT) if str(f).startswith(str(ROOT)) else f
            print(f'  [SKIP] {rel} (이미 callout)')

    print(f'\n=== 요약 ({"DRY-RUN" if dry_run else "EXECUTED"}) ===')
    print(f'  처리: {total}, 변경: {changed}')


if __name__ == '__main__':
    main()
