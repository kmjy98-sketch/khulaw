#!/usr/bin/env python3
"""이진_헌법원리1 + 강성민_헌법OX 두 교재를 헌법 정리노트의 0. 소스 범위 표에 통합 1행으로 추가."""
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브/sync')
TEXTBOOK_ROOT = ROOT / '_교재원문' / '헌법'

# 헌법 노트별 검색 키워드
NOTE_KEYWORDS = {
    # 총론
    '헌법_기본개념': ['헌법.*개념', '헌법.*의의', '실질적.*헌법'],
    '헌정사': ['헌정사', '제헌헌법', '헌법.*개정'],
    '국민주권_대의제': ['국민주권', '대의제', '§1'],
    '관습헌법': ['관습헌법', '수도이전'],
    '법치주의': ['법치주의', '법률유보'],
    '명확성원칙': ['명확성', '명확성원칙'],
    '소급입법금지': ['소급입법', '소급효금지', '진정소급', '부진정소급'],
    '신뢰보호원칙': ['신뢰보호', '신뢰보호원칙'],
    '비례원칙': ['비례원칙', '과잉금지', '§37'],
    '포괄위임금지': ['포괄위임', '위임입법'],
    '평등원칙': ['평등권', '§11', '평등심사'],
    '본질적내용침해금지': ['본질적.*내용', '본질내용침해'],
    '사회국가_국제평화': ['사회국가', '국제평화', '§5'],
    '공무원제도_경제질서': ['공무원제도', '직업공무원', '경제질서', '§7'],
    '정당제도': ['정당', '정당제도', '§8'],
    '선거제도': ['선거', '선거제도', '§24'],
    '지방자치제도': ['지방자치', '§117', '§118'],
    '탄핵소추': ['탄핵소추', '탄핵', '§65'],
    '통치행위': ['통치행위', '사법자제'],
    # 통치구조론
    '국회': ['국회', '입법권', '국회의원'],
    '대통령': ['대통령', '대통령제', '국가원수'],
    '행정부': ['행정부', '국무총리', '국무회의'],
    '법원': ['법원', '사법권', '법관'],
    '헌법재판소_구성': ['헌법재판소', '재판관'],
    '위헌법률심판': ['위헌법률심판', '재판의전제성', '제청'],
    '헌법소원심판': ['헌법소원', '권리구제'],
    '권한쟁의심판': ['권한쟁의'],
    '탄핵_정당해산심판': ['탄핵심판', '정당해산'],
    '정부형태_권력분립': ['정부형태', '권력분립'],
}

TARGET_BOOKS = {
    '이진_헌법원리1': '이진 《헌법원리》 1',
    '강성민_헌법OX': '강성민 《헌법 최종정리 OX》',
}


def grep_chunks(textbook_id: str, keywords: list[str], n: int) -> list[str]:
    book_dir = TEXTBOOK_ROOT / textbook_id
    if not book_dir.exists():
        return []
    pattern = re.compile('|'.join(keywords))
    matches = []
    for f in book_dir.glob(f'{textbook_id}_ch*.md'):
        try:
            text = f.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        count = len(pattern.findall(text))
        if count > 0:
            matches.append((count, f.stem))
    matches.sort(reverse=True)
    return [stem for _, stem in matches[:n]]


def build_row(note_stem: str, textbook_id: str, label: str) -> str | None:
    keywords = NOTE_KEYWORDS.get(note_stem)
    if not keywords:
        return None
    chunks = grep_chunks(textbook_id, keywords, 6)
    if not chunks:
        return None
    links = ', '.join(f'[[{c}]]' for c in chunks)
    kw_str = '·'.join(keywords[:3])
    return f'| {label} | 본문/OX — {kw_str} | {links} |'


SOURCE_HEADER_PAT = re.compile(r'^##\s+0\.\s*소스\s*범위', re.MULTILINE)


def insert_row(text: str, new_row: str, marker: str) -> tuple[str, bool]:
    if marker in text:
        return text, False
    lines = text.split('\n')
    in_source = False
    table_start = None
    table_end = None
    for i, line in enumerate(lines):
        if not in_source:
            if SOURCE_HEADER_PAT.match(line):
                in_source = True
            continue
        if line.strip().startswith('|'):
            if table_start is None:
                table_start = i
            table_end = i
        elif table_start is not None:
            break
    if table_start is None or table_end is None:
        return text, False
    insert_pos = table_end + 1
    lines.insert(insert_pos, new_row)
    return '\n'.join(lines), True


def main():
    dry_run = '--dry-run' in sys.argv
    targets = ['sync/헌법/총론', 'sync/헌법/통치구조론']
    total_files = 0
    changed_files = 0
    skipped_no_keyword = 0
    lee_added = 0
    kang_added = 0

    for t in targets:
        for f in sorted((Path('H:/내 드라이브') / t).glob('*.md')):
            if f.stem.startswith('_'):
                continue
            total_files += 1
            if f.stem not in NOTE_KEYWORDS:
                skipped_no_keyword += 1
                continue
            text = f.read_text(encoding='utf-8')
            changed = False

            # 이진_헌법원리1
            lee_row = build_row(f.stem, '이진_헌법원리1', '이진 《헌법원리》 1 (청크별)')
            if lee_row:
                marker_lee = '이진 《헌법원리》 1 (청크별)'
                if marker_lee not in text:
                    text, inserted = insert_row(text, lee_row, marker_lee)
                    if inserted:
                        lee_added += 1
                        changed = True

            # 강성민_헌법OX
            kang_row = build_row(f.stem, '강성민_헌법OX', '강성민 《헌법 최종정리 OX》')
            if kang_row:
                marker_kang = '강성민 《헌법 최종정리 OX》'
                if marker_kang not in text:
                    text, inserted = insert_row(text, kang_row, marker_kang)
                    if inserted:
                        kang_added += 1
                        changed = True

            if changed:
                if not dry_run:
                    f.write_text(text, encoding='utf-8')
                changed_files += 1

    print(f'=== 헌법잔여 요약 ({"DRY-RUN" if dry_run else "EXECUTED"}) ===')
    print(f'  처리 대상: {total_files}파일')
    print(f'  키워드 정의 없음: {skipped_no_keyword}')
    print(f'  변경된 파일: {changed_files}')
    print(f'  이진 헌법원리1 행 추가: {lee_added}')
    print(f'  강성민 헌법OX 행 추가: {kang_added}')


if __name__ == '__main__':
    main()
