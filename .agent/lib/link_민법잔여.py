#!/usr/bin/env python3
"""송영곤_요건사실론 + 강혜림_민법1(=김준호 민법강의 32판) 두 교재를 정리노트의 0. 소스 범위 표에 통합 1행으로 추가.

각 정리노트의 stem을 키워드로 사용하여 두 교재의 청크를 grep 매칭.
매칭 수가 많은 상위 청크들을 통합 1행으로 0. 소스 범위 표에 삽입.

idempotent: 이미 잔여 행이 있으면 건너뜀.
"""
import sys
import re
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브/sync')
TEXTBOOK_ROOT = ROOT / '_교재원문' / '민법'

# 처리 대상 두 교재
TARGET_BOOKS = {
    '송영곤_요건사실론': '송영곤 《요건사실론》',
    '강혜림_민법1': '김준호 《민법강의》 32판',
}

# link_yoondonghwan과 동일한 NOTE_KEYWORDS (민법 노트 약 100개)
NOTE_KEYWORDS = {
    # 총칙
    '의사표시_통정허위표시': ['통정허위표시', '§108'],
    '의사표시_비진의표시': ['비진의표시', '§107'],
    '의사표시_착오': ['§109', '의사표시.*착오', '동기착오'],
    '의사표시_사기강박': ['§110', '사기.*강박'],
    '의사표시_종합비교': ['의사표시.*비교', '§107', '§108', '§109', '§110'],
    '의사표시_효력발생': ['§111', '도달주의'],
    '표현대리': ['표현대리', '§125', '§126', '§129'],
    '무권대리': ['무권대리', '§130', '§135'],
    '대리_총설': ['§114', '§115', '§116', '대리'],
    '대리권_남용': ['대리권.*남용'],
    '매매': ['매매', '§568', '§569'],
    '반사회적_법률행위': ['반사회적', '§103'],
    '무효와_취소': ['§137', '§141', '취소권'],
    '불법원인급여': ['불법원인급여', '§746'],
    '소멸시효': ['소멸시효', '§162'],
    '제한능력자': ['제한능력자', '§5', '§13'],
    '부재_실종': ['부재.*실종', '§22', '§25'],
    '법인_총설': ['법인.*총설', '§31', '§34'],
    '법인_불법행위능력': ['법인.*불법행위', '§35'],
    '법인_대표권_제한남용': ['대표권.*제한', '대표권.*남용'],
    '비법인사단': ['비법인사단', '총유'],
    '재단법인_출연재산': ['재단법인.*출연', '§47'],
    '신의칙': ['신의칙', '§2'],
    '법률행위_해석': ['법률행위.*해석', '오표시'],
    '조건_기한': ['조건.*기한', '§147', '§152'],
    '계약법_총칙': ['계약.*총칙', '계약자유'],
    '착오와_사기의_관계': ['착오.*사기'],
    # 물권
    '부동산_물권변동': ['§186', '§187', '부동산.*물권변동'],
    '등기의_추정력': ['등기.*추정력'],
    '등기청구권': ['등기청구권'],
    '물권적_청구권': ['§213', '§214', '물권적.*청구'],
    '명의신탁': ['명의신탁', '부동산실명법'],
    '공동소유': ['공유', '합유', '총유'],
    '취득시효': ['취득시효', '§245'],
    '가등기_이중등기': ['가등기', '이중등기'],
    '점유_상호침탈': ['점유', '상호침탈'],
    '물권행위_독자성무인성': ['물권행위.*독자성', '무인성'],
    '도품_유실물': ['도품', '유실물', '§250'],
    '과실수취권_비용상환': ['과실수취', '비용상환', '§201'],
    '소유물반환청구권': ['소유물반환', '§213'],
    '점유침탈_종합비교표': ['점유침탈'],
    '자력구제': ['자력구제'],
    # 담보물권
    '저당권_총론': ['저당권', '§356'],
    '근저당권': ['근저당'],
    '공동저당': ['공동저당', '§368'],
    '양도담보': ['양도담보'],
    '유치권': ['유치권', '§320'],
    '법정지상권': ['법정지상권', '§366'],
    '가등기담보': ['가등기담보', '가담법'],
    '물상대위권': ['물상대위'],
    '비전형담보_개관': ['비전형담보'],
    # 채권총론
    '채무불이행': ['채무불이행', '§390', '이행지체', '이행불능'],
    '계약해제': ['해제', '§543', '§548'],
    '채권양도': ['채권양도', '§449', '§450'],
    '보증채무': ['보증채무', '§428'],
    '채권자대위권': ['채권자대위', '§404'],
    '채권자취소권_사해행위': ['사해행위', '채권자취소', '§406'],
    '변제_총론': ['변제', '§460', '§469'],
    '손해배상액_예정': ['손해배상액', '§398'],
    '연대채무': ['연대채무', '§413'],
    '구상권_변제자대위': ['구상권', '변제자대위'],
    '상계': ['상계', '§492'],
    '공탁': ['공탁', '§487'],
    '대물변제': ['대물변제', '§466'],
    '특정물_종류채권': ['특정물', '종류채권'],
    '금전채권': ['금전채권', '§376'],
    '다수당사자_효력사유': ['다수당사자', '효력사유'],
    '부진정연대채무': ['부진정연대'],
    '채무인수': ['채무인수', '§453'],
    '과실상계': ['과실상계', '§396'],
    '손해배상청구권': ['손해배상청구', '§393'],
    '가산이율': ['가산이율'],
    '채권자취소권_소송요건': ['채권자취소.*소송'],
    '채권자취소권_효력': ['채권자취소.*효력'],
    # 채권각론
    '매도인_담보책임': ['매도인.*담보', '§570', '§580'],
    '동시이행항변권': ['동시이행', '§536'],
    '도급계약': ['도급', '§664'],
    '임대차_총론': ['임대차', '§618'],
    '임대차_보증금': ['임대차.*보증금'],
    '임대차_대항력': ['대항력', '주임법'],
    '임대차_양도': ['임차권.*양도'],
    '임대차_종료': ['임대차.*종료', '갱신'],
    '계약금': ['계약금', '§565'],
    '사용자책임': ['사용자책임', '§756'],
    '공동불법행위': ['공동불법행위', '§760'],
    '계약체결상_과실': ['계약체결.*과실', '§535'],
    '담보책임_채무불이행_경합': ['담보책임.*경합'],
    '급부부당이득': ['부당이득', '§741'],
    '침해부당이득': ['침해부당이득'],
    '특수부당이득': ['특수부당이득'],
    '불법행위_효과': ['불법행위.*효과', '§750'],
    '공작물책임': ['공작물', '§758'],
    '제3자_계약': ['제3자.*계약', '§539'],
    '조합계약': ['조합', '§703'],
    '예금계약': ['예금'],
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
    # 담보물권 보완
    '질권': ['질권', '§329', '§332'],
    '특별법_담보권': ['특별법.*담보', '동산담보권', '채권담보권'],
    # 채권총론 보완
    '경개': ['경개', '§500', '§501'],
    '대상청구권': ['대상청구권', '대상청구'],
    '분할채권_불가분채권': ['분할채권', '불가분채권', '§408'],
    '선택채권': ['선택채권', '§380', '§385'],
    # 채권각론 보완
    '매매_과실수취권': ['매매.*과실', '§587'],
    '매매예약': ['매매예약', '§564', '예약완결권'],
    '사무관리': ['사무관리', '§734'],
    '증여계약': ['증여', '§554', '§555'],
}


def grep_chunks(textbook_id: str, keywords: list[str], n: int) -> list[str]:
    """주어진 교재에서 키워드 매칭 청크 stem 상위 n개."""
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
    """주어진 교재로 통합 1행 생성. 매칭 0건이면 None."""
    keywords = NOTE_KEYWORDS.get(note_stem)
    if not keywords:
        return None
    chunks = grep_chunks(textbook_id, keywords, 6)
    if not chunks:
        return None
    links = ', '.join(f'[[{c}]]' for c in chunks)
    kw_str = '·'.join(keywords[:3])
    return f'| {label} | 본문/사례 — {kw_str} | {links} |'


SOURCE_HEADER_PAT = re.compile(r'^##\s+0\.\s*소스\s*범위', re.MULTILINE)


def insert_row(text: str, new_row: str, marker: str) -> tuple[str, bool]:
    """0. 소스 범위 표에 새 행 삽입. 동일 marker가 이미 본문에 있으면 (text, False)."""
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
    for i in range(table_start, table_end + 1):
        if '김준호' in lines[i] or '강혜림' in lines[i]:
            insert_pos = i
            break
    lines.insert(insert_pos, new_row)
    return '\n'.join(lines), True


def main():
    args = sys.argv[1:]
    dry_run = '--dry-run' in args

    targets = [
        'sync/민법/총칙', 'sync/민법/물권', 'sync/민법/담보물권',
        'sync/민법/채권총론', 'sync/민법/채권각론',
    ]
    total_files = 0
    changed_files = 0
    skipped_no_keyword = 0
    yo_added = 0
    kim_added = 0

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

            # 송영곤_요건사실론
            yo_row = build_row(f.stem, '송영곤_요건사실론', '송영곤 《요건사실론》')
            if yo_row:
                # marker는 stem 일부 (이미 있는지 검사용)
                marker_yo = '송영곤 《요건사실론》'
                if marker_yo not in text:
                    text, inserted = insert_row(text, yo_row, marker_yo)
                    if inserted:
                        yo_added += 1
                        changed = True

            # 강혜림_민법1 (=김준호) — 청크 단위 wikilink만 (기존 _교재목차 행은 유지)
            kim_row = build_row(f.stem, '강혜림_민법1', '김준호 《민법강의》 32판 (청크별)')
            if kim_row:
                marker_kim = '김준호 《민법강의》 32판 (청크별)'
                if marker_kim not in text:
                    text, inserted = insert_row(text, kim_row, marker_kim)
                    if inserted:
                        kim_added += 1
                        changed = True

            if changed:
                if not dry_run:
                    f.write_text(text, encoding='utf-8')
                changed_files += 1

    print(f'=== 민법잔여 요약 ({"DRY-RUN" if dry_run else "EXECUTED"}) ===')
    print(f'  처리 대상: {total_files}파일')
    print(f'  키워드 정의 없음: {skipped_no_keyword}')
    print(f'  변경된 파일: {changed_files}')
    print(f'  요건사실론 행 추가: {yo_added}')
    print(f'  김준호(강혜림_민법1) 청크별 행 추가: {kim_added}')


if __name__ == '__main__':
    main()
