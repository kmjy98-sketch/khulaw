#!/usr/bin/env python3
"""김성돈_형법총론 + 서보학_형법총론 두 교재의 미참조 청크를 형법 정리노트에 통합 1행으로 추가."""
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브/sync')
TEXTBOOK_ROOT = ROOT / '_교재원문' / '형법'

# 형법 노트별 검색 키워드
NOTE_KEYWORDS = {
    # 일반이론
    '죄형법정주의': ['죄형법정주의', '소급효금지', '명확성', '유추해석'],
    '범죄성립_3단계체계': ['구성요건', '위법성', '책임', '범죄성립'],
    '행위론_구성요건론': ['행위론', '구성요건', '인과적행위', '목적적행위'],
    # 구성요건
    '인과관계_객관적귀속': ['인과관계', '객관적.*귀속', '상당인과', '합법칙적'],
    '고의_과실': ['고의', '과실', '미필적'],
    '과실범': ['과실범', '주의의무', '예견가능성'],
    '구성요건적_착오': ['구성요건적.*착오', '사실의.*착오', '방법의.*착오'],
    '결과적_가중범': ['결과적.*가중범', '직접성', '예견가능성'],
    '부작위범': ['부작위범', '보증인', '동가치성'],
    '개괄적_고의': ['개괄적.*고의', '인과과정.*착오'],
    # 위법성
    '위법성론_일반': ['위법성', '위법성조각', '주관적.*정당화'],
    '정당방위': ['정당방위', '§21', '과잉방위'],
    '긴급피난': ['긴급피난', '§22', '과잉피난'],
    '자구행위': ['자구행위', '§23'],
    '정당행위': ['정당행위', '§20', '사회상규'],
    '피해자의_승낙': ['피해자.*승낙', '§24', '양해'],
    '추정적_승낙': ['추정적.*승낙'],
    '위법성조각사유_전제사실착오': ['위법성조각.*전제', '오상.*위법성'],
    '오상방위_우연방위': ['오상방위', '우연방위'],
    # 책임
    '책임론_총론': ['책임', '책임능력', '기대가능성'],
    '원인에있어서자유로운행위': ['원인.*자유.*행위', '원자행위', '§10'],
    '금지착오': ['금지착오', '법률.*착오', '§16'],
    '강요된_행위': ['강요된.*행위', '§12'],
    # 미수
    '미수론': ['미수', '예비', '음모', '장애미수', '중지미수', '불능미수'],
    # 공범
    '정범_공범론': ['공동정범', '간접정범', '교사범', '방조범', '공범'],
}

TARGET_BOOKS = {
    '김성돈_형법총론': '김성돈 《형법총론》 25판 (청크별)',
    '서보학_형법총론': '서보학 《새로 쓴 형법총론》 18판 (청크별)',
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
    return f'| {label} | 본문 — {kw_str} | {links} |'


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
    targets = ['sync/형법/총론']
    total_files = 0
    changed_files = 0
    skipped_no_keyword = 0
    kim_added = 0
    seo_added = 0

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

            kim_row = build_row(f.stem, '김성돈_형법총론', '김성돈 《형법총론》 25판 (청크별)')
            if kim_row:
                marker = '김성돈 《형법총론》 25판 (청크별)'
                if marker not in text:
                    text, inserted = insert_row(text, kim_row, marker)
                    if inserted:
                        kim_added += 1
                        changed = True

            seo_row = build_row(f.stem, '서보학_형법총론', '서보학 《새로 쓴 형법총론》 18판 (청크별)')
            if seo_row:
                marker = '서보학 《새로 쓴 형법총론》 18판 (청크별)'
                if marker not in text:
                    text, inserted = insert_row(text, seo_row, marker)
                    if inserted:
                        seo_added += 1
                        changed = True

            if changed:
                if not dry_run:
                    f.write_text(text, encoding='utf-8')
                changed_files += 1

    print(f'=== 형법잔여 요약 ({"DRY-RUN" if dry_run else "EXECUTED"}) ===')
    print(f'  처리 대상: {total_files}파일')
    print(f'  키워드 정의 없음: {skipped_no_keyword}')
    print(f'  변경된 파일: {changed_files}')
    print(f'  김성돈 행 추가: {kim_added}')
    print(f'  서보학 행 추가: {seo_added}')


if __name__ == '__main__':
    main()
