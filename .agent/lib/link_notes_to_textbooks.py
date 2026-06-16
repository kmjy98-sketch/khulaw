#!/usr/bin/env python3
"""정리노트의 ## 0. 소스 범위 테이블에 교재 청크 위키링크 컬럼을 추가.

- 교재명 매칭 → textbook_id
- 페이지 범위 파싱 → 해당 청크(들) 찾기
- 테이블에 "참조" 컬럼 추가(있으면 갱신), 행마다 [[stem]] 링크
- idempotent: 이미 링크 있는 행은 건너뜀
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from collections import defaultdict

ROOT = Path('H:/내 드라이브')
TEXTBOOK_ROOT = ROOT / 'sync' / '_교재원문'

# 교재명 매칭 규칙: (정규식, textbook_id, 서브책자 힌트)
# 순서 중요: 더 구체적/명시적인 보충자료 규칙을 본책 규칙보다 먼저
MATCH_RULES = [
    # 송영곤 시리즈 — 사례연습2를 본책보다 먼저 (더 구체적)
    (re.compile(r'송영곤.*(?:민사법사례연습\s*2|민사법사례연습2|사례연습\s*2|사례연습2)'), '송영곤_사례연습2', None),
    (re.compile(r'송영곤.*(?:민사법사례연습\s*1|민사법사례연습1|사례연습\s*1)'), '송영곤_사례', None),
    (re.compile(r'송영곤.*(?:요건사실론|요건사실)'), '송영곤_요건사실론', None),
    (re.compile(r'송영곤.*쟁점노트|쟁점노트.*송영곤|민사법쟁점노트'), '송영곤_쟁점노트', None),
    # 보충자료(필기노트·DailyTest·DT선택형·선택형자료·사례 등)는 명시적 키워드일 때만
    (re.compile(r'송영곤.*(?:보충자료|DailyTest|Daily.?Test|DT선택형|선택형.?자료|필기노트|\d+회차)'), '송영곤_논점민법_보충', None),
    # 본책(논점민법강의/기본민법) — 디폴트
    (re.compile(r'송영곤.*(?:기본민법|논점민법|법률행위편|기본민강|논점민강)'), '송영곤_논점민법_본책', None),
    # 민법 기타 미반영 교재 (2026-04-11 2차 이전)
    (re.compile(r'윤동환.*(?:민법의\s*맥|민법의맥|민법의\s*핵심)'), '윤동환_민법의맥', None),
    (re.compile(r'곽낙규.*(?:민법사례연습|사례연습|민사례)'), '곽낙규_사례연습', None),
    (re.compile(r'박승수.*(?:민법기본사례|민법사례|기본사례)'), '박승수_민법기본사례', None),
    (re.compile(r'민법의\s*해석|이계정.*민법|양천수.*민법|권경휘.*민법|이성범.*민법'), '민법의해석', None),
    # 강혜림 민법1 / 김준호 민법강의 32판 (강혜림 폴더에 매핑됨 — 임시 대응)
    (re.compile(r'강혜림.*민법|김준호.*민법강의'), '강혜림_민법1', None),
    # 형법 교재
    (re.compile(r'김기용.*(?:교안|형법총론)'), '김기용_형법교안', None),
    (re.compile(r'김성돈.*(?:형법총론|총론)'), '김성돈_형법총론', None),
    (re.compile(r'서보학.*형법'), '서보학_형법총론', None),
    # 헌법 교재
    (re.compile(r'이진.*헌법|헌법원리1|헌법.*기초이론'), '이진_헌법원리1', None),
    (re.compile(r'강성민.*(?:헌법|OX|최종정리)'), '강성민_헌법OX', None),
    # 선택법 교재
    (re.compile(r'한권탁.*법조윤리|법조윤리.*한권탁|법조윤리.*기출'), '법조윤리_한권탁_기출', None),
]

# 교재별 청크 메타데이터 로드 (frontmatter에서 페이지 범위 추출)
def load_textbook_chunks():
    """{textbook_id: [{'stem','p_start','p_end','book_part'}...]}"""
    chunks = defaultdict(list)
    fm_pat = re.compile(r'^---\n(.*?)\n---', re.DOTALL)
    for tb_dir in TEXTBOOK_ROOT.rglob('*'):
        if not tb_dir.is_dir():
            continue
        if tb_dir.parent.parent.name != '_교재원문':
            continue
        tb_id = tb_dir.name
        for f in tb_dir.glob(f'{tb_id}_ch*.md'):
            text = f.read_text(encoding='utf-8', errors='replace')
            m = fm_pat.match(text)
            if not m:
                continue
            fm = m.group(1)
            p_match = re.search(r'페이지:\s*(\d+)-(\d+)', fm)
            if not p_match:
                # 헌법처럼 페이지 없는 경우 스킵 (별도 처리)
                chunks[tb_id].append({
                    'stem': f.stem,
                    'p_start': None,
                    'p_end': None,
                    'book_part': None,
                })
                continue
            p_start, p_end = int(p_match.group(1)), int(p_match.group(2))
            bp_match = re.search(r'서브책자:\s*(\S+)', fm)
            book_part = bp_match.group(1) if bp_match else None
            chunks[tb_id].append({
                'stem': f.stem,
                'p_start': p_start,
                'p_end': p_end,
                'book_part': book_part,
            })
    return dict(chunks)


def match_textbook(row_text: str) -> str | None:
    """행에서 교재 식별."""
    for pat, tb_id, _ in MATCH_RULES:
        if pat.search(row_text):
            return tb_id
    return None


def extract_page_range(text: str):
    """'p.157~170', 'p.45', 'p. 1025' 등에서 (start,end) 추출."""
    # 범위형
    m = re.search(r'p\.?\s?(\d+)\s*[~\-–]\s*(\d+)', text)
    if m:
        return int(m.group(1)), int(m.group(2))
    # 단일형
    m = re.search(r'p\.?\s?(\d+)', text)
    if m:
        n = int(m.group(1))
        return n, n
    return None, None


# 정리노트 행 텍스트의 키워드 → 교재 book_part 매핑
# (sub-booklet 단위로 과매칭 방지)
BOOK_PART_HINTS = {
    # 송영곤_논점민법_본책 분책
    '법률행위': ['법률행위'],
    '권리대리': ['권리/대리', '대리편', '대리권', '권리편'],
    '물권총론_변동': ['물권총론', '물권변동', '물권편'],
    '소유_점유': ['소유권', '점유', '공유', '용익물권'],
    '채권관계1': ['채권총론', '채권관계'],
    '채권이행_불이행': ['채권이행', '이행불이행', '채무불이행'],
    '채권자지체_3자_변동': ['채권자지체', '제3자', '채권양도', '채무인수'],
    '채권담보': ['채권담보', '연대채무', '보증'],
    '채권각론': ['채권각론'],
    '계약각론': ['계약각론', '계약법'],
    '재산법': ['재산법'],
    '기초법리_민사집행법': ['기초법리', '민사집행', '민사집행법'],
    '민법입문': ['민법입문'],
    # 김성돈 형법총론 분책 (필요 시)
    '구성요건': ['구성요건'],
    '위법성': ['위법성'],
    '책임': ['책임론'],
    '미수': ['미수론'],
    '가담형태': ['공범', '정범', '가담형태'],
    # 송영곤_사례연습2 분책
    '물권법': ['물권법', '물권 사례', '물권사례'],
    '가족법': ['가족법'],
    '채각담보': ['채각담보', '계약각론', '담보'],
    '총론채총': ['총론채총', '민법총칙', '채권총론', '총론'],
    '민사법사례연습2': ['민사법사례연습2', '사례연습2'],
    # 곽낙규_사례연습 분책
    '민법사례연습': ['민법사례연습'],
    '총론,채권총론': ['총론,채권총론', '총론채총'],
    # 박승수 분책
    '물권가족': ['물권가족', '물권', '가족법'],
    '총론채권': ['총론채권', '총론', '채권'],
}


def detect_book_part_hint(row_text: str) -> str | None:
    """행 텍스트에서 book_part 힌트 추출. 가장 먼저 매칭된 part 반환."""
    for part, keywords in BOOK_PART_HINTS.items():
        for kw in keywords:
            if kw in row_text:
                return part
    return None


def find_matching_chunks(
    tb_id: str,
    p_start: int | None,
    p_end: int | None,
    chunks_by_tb: dict,
    book_part_hint: str | None = None,
) -> list[str]:
    """해당 페이지 범위에 걸치는 청크 stem 목록 반환.

    book_part_hint가 주어지면 해당 part의 청크만 후보로 제한 (서브책자 과매칭 방지).
    """
    if tb_id not in chunks_by_tb:
        return []
    candidates = chunks_by_tb[tb_id]
    # 페이지 없으면 — 헌법 등.
    if p_start is None:
        return []
    # book_part 힌트 필터
    if book_part_hint:
        filtered = [c for c in candidates if c.get('book_part') == book_part_hint]
        if filtered:
            candidates = filtered
    hits = []
    for c in candidates:
        if c['p_start'] is None:
            continue
        # 겹치면 선택
        if not (c['p_end'] < p_start or c['p_start'] > p_end):
            hits.append(c['stem'])
    # 힌트 없이 페이지 범위만으로 5개 이상 매칭되면 — 과매칭 — 빈 리스트(목차로 폴백)
    if not book_part_hint and len(hits) > 4:
        return []
    return hits


# 테이블 행 한 줄 처리
ROW_PAT = re.compile(r'^\|([^|\n]+)\|([^|\n]+)\|([^|\n]*)\|?\s*$')


def process_source_table(md_text: str, chunks_by_tb: dict) -> tuple[str, int, list]:
    """## 0. 소스 범위 테이블을 찾아 참조 컬럼 추가.

    반환: (새 본문, 추가된 링크 수, 링크 stem 목록)
    """
    lines = md_text.split('\n')
    added = 0
    all_links = []
    in_source_block = False
    header_idx = None
    sep_idx = None
    rows_start_idx = None
    rows_end_idx = None

    for i, line in enumerate(lines):
        if re.match(r'^##\s+0\.\s*소스\s*범위', line):
            in_source_block = True
            continue
        if in_source_block:
            if re.match(r'^##\s', line) or re.match(r'^---\s*$', line):
                if rows_start_idx is not None and rows_end_idx is None:
                    rows_end_idx = i - 1
                in_source_block = False
                continue
            if line.strip().startswith('|') and '교재' in line and '범위' in line:
                header_idx = i
            elif header_idx is not None and sep_idx is None and line.strip().startswith('|') and '---' in line:
                sep_idx = i
                rows_start_idx = i + 1
            elif sep_idx is not None and line.strip().startswith('|'):
                rows_end_idx = i
            elif sep_idx is not None and not line.strip().startswith('|') and rows_start_idx is not None:
                # 테이블 끝
                if rows_end_idx is None:
                    rows_end_idx = i - 1
                break

    if header_idx is None or sep_idx is None or rows_start_idx is None:
        return md_text, 0, []

    if rows_end_idx is None:
        rows_end_idx = sep_idx  # 빈 테이블 케이스

    # 이미 "참조" 컬럼이 있는지 검사
    header_line = lines[header_idx]
    has_ref_col = '참조' in header_line or '교재원문' in header_line

    new_rows = []
    for ri in range(rows_start_idx, rows_end_idx + 1):
        row = lines[ri]
        # 행의 | 구분자 유지
        cells = [c.strip() for c in row.strip().strip('|').split('|')]
        if len(cells) < 2:
            new_rows.append(row)
            continue
        tb_cell = cells[0]
        range_cell = cells[1]
        tb_id = match_textbook(tb_cell + ' ' + range_cell)
        if not tb_id:
            # 매칭 실패 → 참조 공란
            if has_ref_col and len(cells) >= 3:
                new_rows.append(row)
            else:
                new_row = f"| {tb_cell} | {range_cell} | — |"
                new_rows.append(new_row)
            continue
        p_start, p_end = extract_page_range(range_cell)
        hint = detect_book_part_hint(tb_cell + ' ' + range_cell)
        hits = find_matching_chunks(tb_id, p_start, p_end, chunks_by_tb, book_part_hint=hint)
        if hits:
            # 너무 많으면 앞 3개만 + 요약
            if len(hits) > 3:
                ref_text = ', '.join(f'[[{s}]]' for s in hits[:3]) + f' (+{len(hits)-3}개)'
            else:
                ref_text = ', '.join(f'[[{s}]]' for s in hits)
            all_links.extend(hits)
            added += len(hits)
        else:
            # 매칭은 됐지만 청크 못 찾음 (페이지 없는 헌법 등) → 교재목차로
            ref_text = f'[[_교재목차|{tb_id}]]'
        if has_ref_col and len(cells) >= 3:
            # 기존 참조 셀 교체 (비어있거나 —)
            existing = cells[2]
            if existing and existing not in ('', '—', '-'):
                # 이미 링크 있으면 건너뜀 (idempotent)
                new_rows.append(row)
                continue
            new_row = f"| {tb_cell} | {range_cell} | {ref_text} |"
        else:
            new_row = f"| {tb_cell} | {range_cell} | {ref_text} |"
        new_rows.append(new_row)

    # 헤더/구분자 갱신 (참조 컬럼 없으면 추가)
    if not has_ref_col:
        # 헤더: '| 교재 | 범위 |' → '| 교재 | 범위 | 참조 |'
        h = header_line.rstrip()
        if h.endswith('|'):
            new_header = h + ' 참조 |'
        else:
            new_header = h + ' | 참조 |'
        if not new_header.startswith('|'):
            new_header = '| ' + new_header.lstrip()
        sep_line = lines[sep_idx]
        s = sep_line.rstrip()
        if s.endswith('|'):
            new_sep = s + '------|'
        else:
            new_sep = s + '|------|'
        if not new_sep.startswith('|'):
            new_sep = '|' + new_sep.lstrip()
        lines[header_idx] = new_header
        lines[sep_idx] = new_sep

    # 행 교체
    for idx, new_row in zip(range(rows_start_idx, rows_end_idx + 1), new_rows):
        lines[idx] = new_row

    return '\n'.join(lines), added, all_links


def main():
    chunks_by_tb = load_textbook_chunks()
    print('=== 교재별 청크 로드 ===')
    for tb_id, cs in chunks_by_tb.items():
        print(f'  {tb_id}: {len(cs)}청크')
    print()

    targets = [
        'sync/민법/총칙','sync/민법/물권','sync/민법/담보물권','sync/민법/채권총론','sync/민법/채권각론',
        'sync/형법/총론',
        'sync/헌법/총론','sync/헌법/통치구조론',
    ]
    total_files = 0
    changed_files = 0
    total_added_links = 0
    for t in targets:
        for f in sorted(Path(t).glob('*.md')):
            if f.stem.startswith('_'):
                continue
            total_files += 1
            text = f.read_text(encoding='utf-8')
            new_text, added, links = process_source_table(text, chunks_by_tb)
            if new_text != text:
                f.write_text(new_text, encoding='utf-8')
                changed_files += 1
                total_added_links += added

    print(f'\n=== 요약 ===')
    print(f'  처리 대상: {total_files}파일')
    print(f'  변경된 파일: {changed_files}')
    print(f'  추가된 위키링크: {total_added_links}')


if __name__ == '__main__':
    main()
