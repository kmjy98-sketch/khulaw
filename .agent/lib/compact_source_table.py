#!/usr/bin/env python3
"""0. 소스 범위 표의 같은 저자 행을 통합하여 행 수를 줄임.

그룹화 규칙:
- 송영곤: 본책·쟁점노트·보충자료·사례연습2·요건사실론·사례 → 1행 "송영곤 시리즈"
- 윤동환: 민법의맥 (본책·회차·토큰매칭) → 1행 "윤동환 민법의 맥"
- 김준호: 민법강의 32판 (청크별·_교재목차) → 1행 "김준호 민법강의 32판"
- 곽낙규·박승수·사례연습 시리즈 → 1행 "사례연습 시리즈"
- 김기용·김성돈·서보학: 각 저자별 1행 (형법)
- 이진·강성민: 각 저자별 1행 (헌법)

각 그룹 내 wikilink 합집합. "토큰매칭" suffix 제거.
최대 wikilink 표시: 5개까지 인라인, 나머지는 (+N) 축약.
"""
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path('H:/내 드라이브/sync')

# 그룹 규칙: (패턴, 그룹 키, 통합 라벨)
GROUPS = [
    (r'송영곤', '송영곤', '송영곤 시리즈 (본책·쟁점노트·사례연습·보충자료·요건사실론)'),
    (r'윤동환', '윤동환', '윤동환 《민법의 맥》 24판'),
    (r'김준호|강혜림', '김준호', '김준호 《민법강의》 32판'),
    (r'곽낙규', '곽낙규', '곽낙규 《민법사례연습》'),
    (r'박승수', '박승수', '박승수 《민법기본사례》'),
    (r'민법의해석', '민법의해석', '민법의 해석 (이계정·양천수)'),
    (r'김기용', '김기용', '김기용 《형법총론 교안》 26'),
    (r'김성돈', '김성돈', '김성돈 《형법총론》 25'),
    (r'서보학', '서보학', '서보학 《새로 쓴 형법총론》 18'),
    (r'이진|헌법원리', '이진', '이진 《헌법원리》 1'),
    (r'강성민|헌법OX', '강성민', '강성민 《헌법 최종정리 OX》'),
    (r'한권탁|법조윤리', '한권탁', '법조윤리 한권탁 기출'),
    (r'사례연습 시리즈', '사례연습', '사례연습 시리즈 (곽낙규·박승수·사례연습2)'),
]

SOURCE_HEADER_PAT = re.compile(r'^##\s+0\.\s*(소스\s*범위|범위\s*전제)', re.MULTILINE)
WIKI_PAT = re.compile(r'\[\[[^\]]+\]\]')


def classify_row(row_text: str) -> str | None:
    """행 텍스트에서 그룹 키 추출."""
    for pat, key, _ in GROUPS:
        if re.search(pat, row_text):
            return key
    return None


def extract_wikis(text: str) -> list[str]:
    """텍스트에서 wikilink 추출."""
    return WIKI_PAT.findall(text)


def compact_rows(rows: list[str]) -> list[str]:
    """행 리스트를 그룹별로 압축.

    rows: 데이터 행만 (헤더·구분자 제외)
    """
    groups = {}  # key → {label, ranges: [...], wikis: [...]}
    ungrouped = []  # 분류 안 된 행은 그대로 유지

    for row in rows:
        # `|` 분리
        cells = [c.strip() for c in row.strip().strip('|').split('|')]
        if len(cells) < 2:
            ungrouped.append(row)
            continue
        textbook_cell = cells[0]
        range_cell = cells[1] if len(cells) > 1 else ''
        wikis = []
        for c in cells[2:] if len(cells) > 2 else [cells[1]]:
            wikis.extend(extract_wikis(c))

        key = classify_row(textbook_cell + ' ' + range_cell)
        if key is None:
            ungrouped.append(row)
            continue

        if key not in groups:
            # 그룹 라벨 찾기
            label = next((l for _, k, l in GROUPS if k == key), key)
            groups[key] = {'label': label, 'ranges': [], 'wikis': [], 'order': len(groups)}

        # 범위 텍스트 수집 ((토큰매칭) 제외)
        if '토큰매칭' not in textbook_cell:
            range_text = range_cell.strip()
            if range_text and range_text not in groups[key]['ranges']:
                groups[key]['ranges'].append(range_text)
        # wikilink 수집 (중복 제거, 순서 유지)
        for w in wikis:
            if w not in groups[key]['wikis']:
                groups[key]['wikis'].append(w)

    # 그룹을 GROUPS 순서로 정렬
    order_map = {k: i for i, (_, k, _) in enumerate(GROUPS)}
    sorted_groups = sorted(groups.items(), key=lambda x: order_map.get(x[0], 999))

    # 출력 행 생성
    new_rows = []
    for key, data in sorted_groups:
        label = data['label']
        # 범위는 앞 2개만 (너무 길어지는 것 방지)
        range_str = ' / '.join(data['ranges'][:3])
        if len(data['ranges']) > 3:
            range_str += f' (+{len(data["ranges"]) - 3})'
        # wikilink: 최대 5개 + (+N)
        wikis = data['wikis']
        if len(wikis) <= 5:
            wiki_str = ', '.join(wikis)
        else:
            wiki_str = ', '.join(wikis[:5]) + f' (+{len(wikis) - 5})'
        new_row = f'> | {label} | {range_str} | {wiki_str} |'
        new_rows.append(new_row)

    # 분류 안 된 행 맨 끝에 추가 (`> ` 접두 유지)
    for row in ungrouped:
        if not row.strip().startswith('>'):
            new_rows.append('> ' + row.strip())
        else:
            new_rows.append(row)

    return new_rows


def compact_table(text: str) -> tuple[str, bool]:
    """0. 소스 범위 표를 압축."""
    lines = text.split('\n')
    header_idx = None
    for i, line in enumerate(lines):
        if SOURCE_HEADER_PAT.match(line):
            header_idx = i
            break
    if header_idx is None:
        return text, False

    # callout 안의 표 찾기: `> |` 시작 줄들
    table_start = None
    table_end = None
    for i in range(header_idx + 1, len(lines)):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith('> |') or stripped.startswith('>|'):
            if table_start is None:
                table_start = i
            table_end = i
        elif table_start is not None and not stripped.startswith('>'):
            break
        elif line.startswith('##') or line.startswith('---'):
            break

    if table_start is None or table_end is None:
        return text, False

    # 헤더(2줄: `> | 교재 | 범위 | 참조 |` + `> |----|----|----|`) + 데이터 행
    table_lines = lines[table_start:table_end + 1]
    if len(table_lines) < 3:
        return text, False

    header_row = table_lines[0]
    separator_row = table_lines[1]
    data_rows = table_lines[2:]

    # 데이터 행의 `> ` 접두 제거하여 처리
    clean_data = []
    for r in data_rows:
        if r.strip().startswith('>'):
            clean_data.append(r.lstrip(' >').strip())
        else:
            clean_data.append(r.strip())

    # 압축
    new_data_rows = compact_rows(clean_data)

    # 새 표 조립
    new_table = [header_row, separator_row] + new_data_rows

    # 교체
    new_lines = lines[:table_start] + new_table + lines[table_end + 1:]

    # callout 메타 정보 업데이트 (교재 수, 청크 수)
    # header_idx + 1 또는 header_idx + 2 근처에 callout 헤더 있을 것
    for i in range(header_idx + 1, min(header_idx + 4, len(new_lines))):
        line = new_lines[i]
        if '[!note]' in line and '📚' in line:
            # 새 wikilink 수 세기
            total_wikis = sum(len(extract_wikis(r)) for r in new_data_rows)
            book_count = len([r for r in new_data_rows if '|' in r and '그룹' not in r])
            new_lines[i] = re.sub(
                r'\(\d+개 교재.*?\)',
                f'({book_count}개 저자, 압축됨)',
                line
            )
            break

    return '\n'.join(new_lines), True


def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args
    args = [a for a in args if a != '--dry-run']

    if args:
        targets = [Path(a) for a in args]
    else:
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
        new_text, modified = compact_table(text)
        if modified:
            if not dry_run:
                f.write_text(new_text, encoding='utf-8')
            changed += 1
            rel = f.relative_to(ROOT) if str(f).startswith(str(ROOT)) else f
            print(f'  [OK] {rel}')
        else:
            rel = f.relative_to(ROOT) if str(f).startswith(str(ROOT)) else f
            print(f'  [SKIP] {rel}')

    print(f'\n=== 요약 ({"DRY-RUN" if dry_run else "EXECUTED"}) ===')
    print(f'  처리: {total}, 변경: {changed}')


if __name__ == '__main__':
    main()
