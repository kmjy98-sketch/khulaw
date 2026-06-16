#!/usr/bin/env python3
"""파일명 토큰 기반 청크-노트 매칭.

재명명 후 청크 파일명이 쟁점 기반이 되었으므로,
청크 stem의 토큰과 정리노트 stem의 토큰을 직접 매칭하여
미참조 청크에 wikilink를 추가한다.
"""
import sys
import re
import json
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path('H:/내 드라이브/sync')

# 수동 추가 쟁점 토큰 (chunk_extra_tokens.json)
EXTRA_TOKENS_FILE = Path('H:/내 드라이브/.agent/state/chunk_extra_tokens.json')
try:
    with open(EXTRA_TOKENS_FILE, 'r', encoding='utf-8') as f:
        EXTRA_TOKENS = json.load(f)
    print(f'수동 토큰 로드: {len(EXTRA_TOKENS)}개')
except FileNotFoundError:
    EXTRA_TOKENS = {}

# 제외 토큰 (너무 일반적이어서 매칭 의미 없음)
STOP_TOKENS = {
    '총론', '일반', '총설', '기초이론', '기초', '개관', '서론', '서문', '머리말',
    '목차', '색인', '판례색인', '참고문헌', '사항색인', '부록',
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12',
    '송영곤', '김기용', '김성돈', '서보학', '곽낙규', '박승수', '윤동환',
    '강혜림', '이진', '강성민', '민법의해석', '김준호', '한권탁',
    '논점민법', '민법강의', '형법총론', '형법교안', '민법의맥', '사례연습',
    '쟁점노트', '요건사실론', '민법기본사례', '헌법원리1', '헌법OX', '법조윤리',
    '기출', '문제', '해설', '연습문제', '회차', '필기', '노트', '보충',
    '본책', '교재', '논점민법보충', '민법의해석', '사례', '보완자료',
    '보충자료', '강의', 'DT', '선택형', '선택형자료', '주요사례',
    '종합판', '종합', '교재판', '총론채총판', '민법', '형법', '헌법',
    '1부', '2부', '3부', '4부', '5부', '6부',
    '1차', '2차', '3차', '4차', '5차', '6차',
    'p0001', 'p0031', 'p0061', 'p0091', 'p0121',
    '25년', '26년', '24년',
    'ch01', 'ch02', 'ch03',
    '민총A', '민총B', '물권A', '물권B', '채각A', '채각B', '채총A', '채총B',
    '친상A', '친상B', '사례1', '사례2', '민총단편', '본1', '본2', '본3',
}


def tokenize(stem: str) -> set[str]:
    """파일명을 _로 분리하여 의미 토큰 추출. 복합 토큰도 부분 일치로 분해."""
    tokens = set()
    for raw in stem.split('_'):
        raw = raw.strip()
        if not raw:
            continue
        if raw in STOP_TOKENS:
            continue
        if raw.startswith('ch') and raw[2:].isdigit():
            continue
        if raw.startswith('p') and raw[1:].replace('-', '').isdigit():
            continue
        # "5회" "10회차" 같은 회차 표기 제외
        if re.match(r'^\d+회(차)?$', raw):
            continue
        if len(raw) < 2:
            continue
        tokens.add(raw)
        # 복합 토큰 부분 일치를 위한 추가 (2~4글자 접두 포함)
        # 예: "법인기관" → "법인", "기관" 별도 추가
        # 주요 법학 키워드 사전으로 분해
        for kw in LEGAL_KEYWORDS:
            if kw in raw and kw != raw:
                tokens.add(kw)
    return tokens


# 법학 핵심 키워드 (복합 토큰에서 부분 추출)
LEGAL_KEYWORDS = [
    # 민법 총칙
    '법인', '신의칙', '권리능력', '행위능력', '제한능력자', '의사능력',
    '법률행위', '반사회적', '불공정', '통정허위표시', '비진의표시',
    '착오', '사기', '강박', '대리', '복대리', '표현대리', '무권대리',
    '무효', '취소', '조건', '기한', '소멸시효', '제척기간',
    '부재', '실종', '재단법인', '비법인사단', '권리주체',
    # 물권
    '물권', '점유', '소유권', '등기', '물권변동', '명의신탁', '취득시효',
    '공유', '합유', '총유', '지상권', '전세권', '유치권', '질권',
    '저당권', '근저당권', '가등기', '양도담보', '법정지상권', '물상대위',
    '선의취득', '부합', '상린관계', '물권적청구권',
    # 채권총론
    '채권', '채무', '이행', '불이행', '이행지체', '이행불능', '불완전이행',
    '손해배상', '과실상계', '배상액', '위약금', '지연손해금',
    '채권자대위', '채권자취소', '사해행위', '이해관계', '피보전채권',
    '연대채무', '보증', '보증채무', '구상권', '변제자대위',
    '변제', '공탁', '상계', '대물변제', '경개', '혼동', '면제',
    '채권양도', '채무인수', '지명채권', '대항요건', '이의유보',
    '다수당사자', '분할채권', '불가분채권', '부진정연대',
    # 채권각론
    '매매', '교환', '증여', '소비대차', '임대차', '전대', '임차권',
    '도급', '위임', '고용', '조합', '화해', '예금',
    '계약', '해제', '해지', '동시이행', '위험부담', '대상청구권',
    '계약금', '해약금', '담보책임', '하자담보',
    '불법행위', '공동불법행위', '사용자책임', '공작물책임', '감독자책임',
    '부당이득', '불법원인급여', '급부부당이득', '침해부당이득',
    '사무관리', '대상청구',
    # 가족법·상속
    '혼인', '이혼', '친권', '부모자', '양자', '부양', '재산분할',
    '상속', '상속인', '유언', '유류분', '상속포기',
    # 형법
    '구성요건', '위법성', '책임', '미수', '공범',
    '죄형법정주의', '명확성원칙', '소급효금지', '유추해석',
    '인과관계', '객관적귀속', '고의', '과실', '미필적',
    '정당방위', '긴급피난', '자구행위', '정당행위', '피해자승낙',
    '추정적승낙', '위전착', '위법성조각사유',
    '책임능력', '기대가능성', '원자행위', '금지착오', '강요된행위',
    '구성요건적착오', '장애미수', '중지미수', '불능미수', '예비',
    '공동정범', '간접정범', '교사범', '방조범', '필요적공범',
    '부작위범', '결과적가중범', '개괄적고의',
    '죄수론', '경합범', '포괄일죄', '상상적경합',
    '형의양정', '가중감경', '집행유예', '보안처분',
    # 헌법
    '헌법', '기본권', '비례원칙', '평등원칙', '법치주의', '신뢰보호',
    '포괄위임', '적법절차', '소급입법', '행복추구권', '인간존엄',
    '직업자유', '재산권', '종교자유', '집회자유', '표현자유',
    '참정권', '청구권', '사회권', '근로3권', '교육권',
    '국민주권', '대의제', '선거', '정당', '지방자치', '공무원',
    '국회', '대통령', '행정부', '법원', '헌법재판소',
    '위헌법률심판', '헌법소원', '권한쟁의', '탄핵', '정당해산',
    '통치행위', '권력분립', '관습헌법',
]



def collect_notes() -> dict[str, set[str]]:
    """정리노트 stem → 토큰 집합. stem + aliases + frontmatter 쟁점 포함."""
    notes = {}
    fm_pat = re.compile(r'^---\n(.*?)\n---', re.DOTALL)
    alias_pat = re.compile(r'aliases:\s*\[([^\]]+)\]')
    tags_pat = re.compile(r'tags:\s*\[([^\]]+)\]')
    for src in ['민법', '형법', '헌법']:
        for f in (ROOT / src).rglob('*.md'):
            if f.stem.startswith('_'):
                continue
            text = f.read_text(encoding='utf-8', errors='replace')
            tokens = tokenize(f.stem)
            # aliases
            m = fm_pat.match(text)
            if m:
                fm = m.group(1)
                am = alias_pat.search(fm)
                if am:
                    for a in am.group(1).split(','):
                        a = a.strip().strip('"').strip("'")
                        # § 제거 후 토큰화
                        a_clean = a.replace('§', '').replace(' ', '').replace('·', '')
                        if a_clean and len(a_clean) >= 2 and a_clean not in STOP_TOKENS:
                            tokens.add(a_clean)
                tm = tags_pat.search(fm)
                if tm:
                    for t in tm.group(1).split(','):
                        t = t.strip()
                        if t and len(t) >= 2 and t not in STOP_TOKENS:
                            tokens.add(t)
            notes[f.stem] = (f, tokens)
    return notes


def collect_chunks() -> list[tuple[str, Path, set[str]]]:
    """sync/_교재원문/ 전체 청크 (stem, path, tokens). extra_tokens 병합."""
    chunks = []
    for f in (ROOT / '_교재원문').rglob('*.md'):
        if f.stem.startswith('_'):
            continue
        tokens = tokenize(f.stem)
        # 수동 추가 토큰 병합
        extra = EXTRA_TOKENS.get(f.stem, [])
        for t in extra:
            if t and len(t) >= 2:
                tokens.add(t)
        if tokens:
            chunks.append((f.stem, f, tokens))
    return chunks


def get_linked_stems() -> set[str]:
    """현재 wikilink로 참조되는 모든 stem."""
    linked = set()
    link_pat = re.compile(r'\[\[([^\]|#]+)(?:\|[^\]]+)?(?:#[^\]]+)?\]\]')
    for src in ['민법', '형법', '헌법']:
        for f in (ROOT / src).rglob('*.md'):
            text = f.read_text(encoding='utf-8', errors='replace')
            for link in link_pat.findall(text):
                linked.add(link.strip().split('/')[-1])
    return linked


def find_textbook_label(chunk_path: Path) -> str:
    """청크 경로에서 교재 디렉터리명 추출."""
    parts = chunk_path.parts
    # sync/_교재원문/{과목}/{교재}/{파일}
    try:
        idx = parts.index('_교재원문')
        return parts[idx + 2]
    except (ValueError, IndexError):
        return 'unknown'


SOURCE_HEADER_PAT = re.compile(r'^##\s+0\.\s*소스\s*범위', re.MULTILINE)


def insert_matched_row(text: str, label: str, chunk_stems: list[str]) -> tuple[str, bool]:
    """0. 소스 범위 표에 새 매칭 행 삽입. 이미 해당 label 행이 있으면 skip."""
    marker = f'| {label} (토큰매칭)'
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
    links = ', '.join(f'[[{c}]]' for c in chunk_stems[:8])  # 최대 8개
    new_row = f'| {label} (토큰매칭) | 재명명 후 쟁점 매칭 | {links} |'
    insert_pos = table_end + 1
    for i in range(table_start, table_end + 1):
        if '김준호' in lines[i] or '강혜림' in lines[i]:
            insert_pos = i
            break
    lines.insert(insert_pos, new_row)
    return '\n'.join(lines), True


def main():
    print('정리노트 수집...')
    notes = collect_notes()
    print(f'  → {len(notes)}개')

    print('청크 수집...')
    chunks = collect_chunks()
    print(f'  → {len(chunks)}개')

    print('기존 wikilink 수집...')
    linked = get_linked_stems()
    print(f'  → {len(linked)}개')

    # 미참조 청크만 필터
    unlinked_chunks = [(stem, path, tokens) for stem, path, tokens in chunks if stem not in linked]
    print(f'미참조 청크: {len(unlinked_chunks)}개')

    # 각 정리노트별로 매칭 점수 계산
    # 점수 = 토큰 겹침 수
    note_to_chunks = defaultdict(list)  # note_stem → [(chunk_stem, chunk_path, score)]
    for c_stem, c_path, c_tokens in unlinked_chunks:
        best_matches = []
        for n_stem, (n_path, n_tokens) in notes.items():
            overlap = c_tokens & n_tokens
            if len(overlap) >= 1:
                score = len(overlap)
                best_matches.append((n_stem, score))
        # 점수 순 상위 3개 노트에 연결
        best_matches.sort(key=lambda x: -x[1])
        for n_stem, score in best_matches[:3]:
            note_to_chunks[n_stem].append((c_stem, c_path, score))

    # 각 노트별로 최대 8개 청크만 (점수 순)
    for n_stem in note_to_chunks:
        note_to_chunks[n_stem].sort(key=lambda x: -x[2])
        note_to_chunks[n_stem] = note_to_chunks[n_stem][:8]

    # 교재별로 분리: 같은 노트에 여러 교재의 청크가 매칭되므로 교재별 행 생성
    # note_stem → textbook → [chunk_stem, ...]
    note_book_chunks = defaultdict(lambda: defaultdict(list))
    for n_stem, matches in note_to_chunks.items():
        for c_stem, c_path, score in matches:
            book = find_textbook_label(c_path)
            note_book_chunks[n_stem][book].append(c_stem)

    print(f'\n매칭된 정리노트: {len(note_book_chunks)}개')

    # 실제 편집
    total_added = 0
    changed_files = 0
    new_wikilinks = 0
    for n_stem, books in note_book_chunks.items():
        f, _ = notes[n_stem]
        text = f.read_text(encoding='utf-8')
        modified = False
        for book, chunk_stems in books.items():
            new_text, inserted = insert_matched_row(text, book, chunk_stems)
            if inserted:
                text = new_text
                total_added += 1
                new_wikilinks += len(chunk_stems)
                modified = True
        if modified:
            f.write_text(text, encoding='utf-8')
            changed_files += 1

    print(f'\n=== 요약 ===')
    print(f'  변경 노트: {changed_files}')
    print(f'  추가 행: {total_added}')
    print(f'  추가 wikilink: {new_wikilinks}')


if __name__ == '__main__':
    main()
