#!/usr/bin/env python3
"""사례연습 시리즈(곽낙규·박승수·송영곤_사례연습2·송영곤_사례)를 정리노트의 0. 소스 범위 표에 통합 1행으로 추가.

각 정리노트의 stem을 키워드로 사용하여 사례연습 책의 청크를 grep 매칭.
매칭 수가 많은 상위 청크들을 통합 1행으로 0. 소스 범위 표에 삽입.

idempotent: 이미 사례연습 시리즈 행이 있으면 건너뜀.
"""
import sys
import re
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브/sync')
TEXTBOOK_ROOT = ROOT / '_교재원문' / '민법'

CASE_TEXTBOOKS = ['곽낙규_사례연습', '박승수_민법기본사례', '송영곤_사례연습2', '송영곤_사례']

# 정리노트 stem → 검색 키워드 매핑
NOTE_KEYWORDS = {
    # 총칙
    '의사표시_통정허위표시': ['통정허위표시', '§108'],
    '표현대리': ['표현대리', '§125', '§126', '§129'],
    '무권대리': ['무권대리', '§130', '§135'],
    '매매': ['매매', '매도인', '매수인', '§568'],
    '반사회적_법률행위': ['반사회적', '§103'],
    '의사표시_착오': ['§109', '동기착오', '의사표시.*착오'],
    '의사표시_사기강박': ['§110', '사기.*강박', '강박'],
    '대리권_남용': ['대리권.*남용', '대리권남용'],
    '무효와_취소': ['§137', '§141', '취소권'],
    '불법원인급여': ['불법원인급여', '§746'],
    '소멸시효': ['소멸시효', '§162'],
    # 물권
    '부동산_물권변동': ['§186', '§187', '부동산.*물권변동'],
    '등기의_추정력': ['등기.*추정력', '추정력'],
    '등기청구권': ['등기청구권'],
    '명의신탁': ['명의신탁', '부동산실명법'],
    '공동소유': ['공유', '합유', '총유', '§262'],
    '취득시효': ['취득시효', '§245'],
    '물권적_청구권': ['§213', '§214', '물권적.*청구'],
    '가등기_이중등기': ['가등기', '이중등기'],
    '점유_상호침탈': ['점유', '상호침탈'],
    # 담보물권
    '저당권_총론': ['저당권', '§356'],
    '근저당권': ['근저당'],
    '공동저당': ['공동저당', '§368'],
    '양도담보': ['양도담보'],
    '유치권': ['유치권', '§320'],
    '법정지상권': ['법정지상권', '§366'],
    '가등기담보': ['가등기담보', '가담법'],
    # 채권총론
    '채무불이행': ['채무불이행', '§390', '이행지체', '이행불능'],
    '계약해제': ['해제', '해지', '§543', '§548'],
    '채권양도': ['채권양도', '§449', '§450'],
    '보증채무': ['보증채무', '§428', '보증인'],
    '채권자대위권': ['채권자대위', '§404'],
    '채권자취소권_사해행위': ['사해행위', '채권자취소', '§406'],
    '변제_총론': ['변제', '§460', '§469'],
    '손해배상액_예정': ['손해배상액', '§398'],
    '연대채무': ['연대채무', '§413'],
    '구상권_변제자대위': ['구상권', '변제자대위'],
    '상계': ['상계', '§492'],
    '공탁': ['공탁', '§487'],
    # 채권각론
    '매도인_담보책임': ['매도인.*담보', '§570', '§580'],
    '동시이행항변권': ['동시이행', '§536'],
    '도급계약': ['도급', '§664'],
    '임대차_총론': ['임대차', '§618'],
    '임대차_보증금': ['임대차.*보증금', '보증금반환'],
    '임대차_대항력': ['대항력', '주임법'],
    '임대차_양도': ['임차권.*양도', '전대'],
    '임대차_종료': ['임대차.*종료', '갱신'],
    '계약금': ['계약금', '해약금', '§565'],
    '사용자책임': ['사용자책임', '§756'],
    '공동불법행위': ['공동불법행위', '§760'],
    '계약체결상_과실': ['계약체결.*과실', '§535'],
    '담보책임_채무불이행_경합': ['담보책임.*경합', '하자.*확대손해'],
    '동산_부동산_부합': ['부합', '§256', '§257'],
    '급부부당이득': ['부당이득', '§741', '급부'],
    '침해부당이득': ['침해부당이득', '침해이득'],
    '특수부당이득': ['특수부당이득'],
    '불법행위_효과': ['불법행위.*효과', '§750'],
    '공작물책임': ['공작물', '§758'],
    '제3자_계약': ['제3자.*계약', '§539'],
    '조합계약': ['조합', '§703'],
    '예금계약': ['예금', '예금계약'],
    '전대차': ['전대차', '§629'],
    '토지거래허가': ['토지거래허가', '국토법'],
    # 물권 보완
    '동산_물권변동': ['동산.*물권변동', '§188', '§189', '§190'],
    '명인방법_물권소멸': ['명인방법', '물권소멸'],
    '물권_총론': ['물권법정주의', '§185', '물권.*효력'],
    '미등기_무허가건물': ['미등기.*건물', '무허가건물'],
    '법률행위외_물권변동': ['§187', '법률.*규정'],
    '본권에의한항변': ['본권.*항변', '소유권.*항변'],
    '상린관계': ['상린관계', '§215', '§216', '§217'],
    '선의취득': ['선의취득', '§249'],
    '소유권_일반': ['소유권', '§211'],
    '전세권': ['전세권', '§303', '§312'],
    '점유_총설': ['점유.*총설', '점유권', '§192'],
    '점유보호청구권': ['점유보호청구권', '§204', '§205'],
    '중간생략등기': ['중간생략', '중간생략등기'],
    '지상권': ['지상권', '§279', '§280'],
    '지역권': ['지역권', '§291'],
    '첨부': ['첨부', '§256', '§257', '§258'],
    '질권': ['질권', '§329', '§332'],
    '특별법_담보권': ['특별법.*담보', '동산담보권', '채권담보권'],
    '경개': ['경개', '§500', '§501'],
    '대상청구권': ['대상청구권', '대상청구'],
    '분할채권_불가분채권': ['분할채권', '불가분채권', '§408'],
    '선택채권': ['선택채권', '§380', '§385'],
    '매매_과실수취권': ['매매.*과실', '§587'],
    '매매예약': ['매매예약', '§564', '예약완결권'],
    '사무관리': ['사무관리', '§734'],
    '증여계약': ['증여', '§554', '§555'],
}


def grep_chunks(textbook_id: str, keywords: list[str]) -> list[str]:
    """주어진 교재에서 키워드 OR 매칭되는 청크 stem 목록 (매칭 수 내림차순)."""
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
    return [stem for _, stem in matches]


def select_top_chunks(textbook_id: str, keywords: list[str], n: int) -> list[str]:
    """매칭 수 상위 n개 청크 stem 반환."""
    return grep_chunks(textbook_id, keywords)[:n]


def build_case_row(note_stem: str) -> str | None:
    """노트 stem에 맞춰 사례연습 통합 1행 생성. 모두 0개면 None."""
    keywords = NOTE_KEYWORDS.get(note_stem)
    if not keywords:
        return None
    parts = []
    # 책별로 1~2개 청크씩 선택
    quotas = {
        '곽낙규_사례연습': 2,
        '박승수_민법기본사례': 2,
        '송영곤_사례연습2': 2,
        '송영곤_사례': 1,
    }
    book_label = {
        '곽낙규_사례연습': '곽낙규',
        '박승수_민법기본사례': '박승수',
        '송영곤_사례연습2': '사례연습2',
        '송영곤_사례': '송영곤사례',
    }
    selected_links = []
    selected_labels = []
    for tb_id, quota in quotas.items():
        chunks = select_top_chunks(tb_id, keywords, quota)
        for c in chunks:
            selected_links.append(f'[[{c}]]')
        if chunks:
            selected_labels.append(book_label[tb_id])

    if not selected_links:
        return None

    label_str = '·'.join(selected_labels)
    kw_str = '·'.join(keywords[:3])
    return f'| 사례연습 시리즈 ({label_str}) | 사례 — {kw_str} | {", ".join(selected_links)} |'


# 0. 소스 범위 표 안에 사례연습 행 삽입
SOURCE_HEADER_PAT = re.compile(r'^##\s+0\.\s*소스\s*범위', re.MULTILINE)
TABLE_ROW_PAT = re.compile(r'^\|.*\|.*\|\s*$')


def insert_case_row(text: str, new_row: str) -> tuple[str, bool]:
    """노트 본문에 사례연습 행 삽입. 이미 있으면 (text, False) 반환."""
    if '사례연습 시리즈' in text:
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
            # 표 끝
            break
    if table_start is None or table_end is None:
        return text, False
    # 표 마지막 행 다음에 삽입 (김준호 행이 마지막인 경우 그 앞에 삽입하는 것이 좋지만 단순하게 마지막에 삽입)
    # 실제로는 김준호 행 앞에 삽입
    insert_pos = table_end + 1
    for i in range(table_start, table_end + 1):
        if '김준호' in lines[i] or '강혜림' in lines[i]:
            insert_pos = i
            break
    lines.insert(insert_pos, new_row)
    return '\n'.join(lines), True


def main():
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print('=== DRY RUN ===\n')

    targets = [
        'sync/민법/총칙', 'sync/민법/물권', 'sync/민법/담보물권',
        'sync/민법/채권총론', 'sync/민법/채권각론',
    ]
    total_files = 0
    changed_files = 0
    skipped_no_keyword = 0
    skipped_no_match = 0

    for t in targets:
        for f in sorted((Path('H:/내 드라이브') / t).glob('*.md')):
            if f.stem.startswith('_'):
                continue
            total_files += 1
            if f.stem not in NOTE_KEYWORDS:
                skipped_no_keyword += 1
                continue
            new_row = build_case_row(f.stem)
            if not new_row:
                skipped_no_match += 1
                continue
            text = f.read_text(encoding='utf-8')
            new_text, inserted = insert_case_row(text, new_row)
            if inserted:
                if not dry_run:
                    f.write_text(new_text, encoding='utf-8')
                changed_files += 1
                rel = f.relative_to(Path('H:/내 드라이브'))
                print(f'[{rel}]')
                print(f'  {new_row[:200]}')

    print()
    print('=== 요약 ===')
    print(f'  처리 대상: {total_files}파일')
    print(f'  키워드 정의 없음 (건너뜀): {skipped_no_keyword}')
    print(f'  매칭 0건 (건너뜀): {skipped_no_match}')
    print(f'  변경된 파일: {changed_files}')


if __name__ == '__main__':
    main()
