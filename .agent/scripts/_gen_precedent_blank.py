#!/usr/bin/env python3
"""채운 판례의 판결요지/결정요지에서 블랭크 문제 자동 생성.

마스킹 대상:
  - 조문번호: `제\\d+조(?:\\s*제\\d+항)?(?:\\s*제\\d+호)?`
  - 기간·수치: `\\d+년`, `\\d+개월`, `\\d+일`, `\\d+%`
  - 판례 결론 키워드: 무효/유효, 적법/위법, 위배(된다|되지 아니한다), 침해(된다|되지 아니한다)
  - 주체 키워드: 선의/악의, 과실/중과실, 경과실, 고의, 과실상계
  - 법률효과: 취소, 해제, 해지, 무효, 취소할 수 있다

한 문단당 최대 3개까지만 마스킹(난이도·가독성 고려). 같은 표현 중복 마스킹 방지.
결과: `.agent/state/precedent_problems_blank_2026-04-18.json`
  각 문항에 references: {case_stub_link, sources: [{book_name, context_path, page?}]} 포함.
"""
import re
import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브/sync/_백업/교재원문_문서_백업_2026-05-22/_판례색인')
TEXTBOOK_ROOT = Path('H:/내 드라이브/sync/_백업/교재원문_문서_백업_2026-05-22/_교재원문')
OUT_PATH = Path('H:/내 드라이브/.agent/state/precedent_problems_blank_2026-04-18.json')

# 페이지 마커 패턴: [p.123], p.123, P.123
PAGE_MARKER_RE = re.compile(
    r'\[p\.\s*(\d+)\]'
    r'|(?<![A-Za-z])p\.\s*(\d+)'
    r'|(?<![A-Za-z])P\.\s*(\d+)'
)
PAGE_WINDOW = 200

MAX_BLANKS_PER_PARAGRAPH = 3
MIN_PARAGRAPH_LEN = 40  # 너무 짧은 문단 건너뜀


def parse_sources_table(body: str) -> list:
    """## 출현 교재 (상위 20건) 표 파싱 → [{book_name, context_path}, ...]."""
    in_sec = False
    rows = []
    for line in body.split('\n'):
        s = line.strip()
        if re.match(r'^##\s+출현 교재', s):
            in_sec = True
            continue
        if in_sec:
            if s.startswith('## '):
                break
            if not s.startswith('|'):
                continue
            if '교재 파일' in s or re.match(r'^\|[-| ]+\|$', s):
                continue
            parts = [p.strip() for p in s.split('|')]
            parts = [p for p in parts if p]
            if len(parts) < 2:
                continue
            book = re.sub(r'\[\[([^\]]+)\]\]', r'\1', parts[0])
            ctx = parts[1].strip('`').strip()
            rows.append({'book_name': book, 'context_path': ctx})
    return rows


def find_page_in_context(context_path: str, case_number: str) -> str:
    """컨텍스트 파일에서 판례번호 주변 페이지 마커 탐색. 없으면 ''."""
    full_path = TEXTBOOK_ROOT / context_path
    if not full_path.exists():
        return ''
    try:
        text = full_path.read_text(encoding='utf-8')
    except Exception:
        return ''
    case_pat = re.compile(re.escape(case_number))
    for m in case_pat.finditer(text):
        start = max(0, m.start() - PAGE_WINDOW)
        end = min(len(text), m.end() + PAGE_WINDOW)
        window = text[start:end]
        pm = PAGE_MARKER_RE.search(window)
        if pm:
            num = pm.group(1) or pm.group(2) or pm.group(3)
            return f'p.{num}'
    return ''

# 우선순위 높은 순서로 정의. 매칭되면 해당 토큰을 빈칸 후보로.
BLANK_PATTERNS = [
    # 조문 참조 — 가장 정보량 크므로 최우선
    (re.compile(r'(?:민법|형법|헌법|형사소송법|민사소송법|상법)\s*제\s*\d+\s*조(?:\s*제\s*\d+\s*항)?(?:\s*제\s*\d+\s*호)?'), '조문'),
    (re.compile(r'제\s*\d+\s*조(?:\s*제\s*\d+\s*항)?(?:\s*제\s*\d+\s*호)?'), '조문'),
    # 기간·수치
    (re.compile(r'\d{1,3}\s*년'), '기간'),
    (re.compile(r'\d{1,3}\s*개월'), '기간'),
    (re.compile(r'\d{1,3}\s*일'), '기간'),
    (re.compile(r'\d{1,3}\s*%'), '수치'),
    # 효과·판단 결론
    (re.compile(r'위배되지\s*아니한다'), '결론'),
    (re.compile(r'위배된다'), '결론'),
    (re.compile(r'침해되지\s*아니한다'), '결론'),
    (re.compile(r'침해된다'), '결론'),
    (re.compile(r'무효로?\s*한다'), '효과'),
    (re.compile(r'유효하다'), '효과'),
    (re.compile(r'취소할\s*수\s*있다'), '효과'),
    (re.compile(r'적법하다'), '결론'),
    (re.compile(r'위법하다'), '결론'),
    # 주체/주관 용어
    (re.compile(r'선의[ㆍ·]?무과실'), '주관'),
    (re.compile(r'선의[ㆍ·]?악의'), '주관'),
    (re.compile(r'악의'), '주관'),
    (re.compile(r'선의'), '주관'),
    (re.compile(r'중과실'), '주관'),
    (re.compile(r'경과실'), '주관'),
    (re.compile(r'과실상계'), '주관'),
    (re.compile(r'고의'), '주관'),
]


def read_md(p: Path) -> tuple[dict, str]:
    text = p.read_text(encoding='utf-8')
    if not text.startswith('---'):
        return {}, text
    end = text.find('\n---', 3)
    if end < 0:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 4:].lstrip('\n')
    fm = {}
    for line in fm_text.split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()
    return fm, body


def extract_summary_block(body: str) -> list[str]:
    """판결요지/결정요지 콜아웃 블록의 각 줄 반환."""
    lines = []
    in_block = False
    for line in body.split('\n'):
        s = line.strip()
        if s.startswith('> [!판례] 판결요지') or s.startswith('> [!판례] 결정요지'):
            in_block = True
            continue
        if in_block:
            if s.startswith('> [!판례]') or s.startswith('## '):
                break
            if not s.startswith('>'):
                break
            stripped = s.lstrip('>').strip()
            if stripped:
                lines.append(stripped)
    return lines


def blank_paragraph(text: str) -> tuple[str, list[dict]]:
    """한 문단에서 마스킹 후보를 찾아 블랭크 처리.

    같은 표현 중복 마스킹 방지: 이미 마스킹된 구간은 건너뜀.
    """
    answers = []
    masked_spans = []  # (start, end)

    def overlaps(a, b):
        return not (a[1] <= b[0] or b[1] <= a[0])

    for pat, kind in BLANK_PATTERNS:
        if len(answers) >= MAX_BLANKS_PER_PARAGRAPH:
            break
        for m in pat.finditer(text):
            if len(answers) >= MAX_BLANKS_PER_PARAGRAPH:
                break
            span = (m.start(), m.end())
            if any(overlaps(span, s) for s in masked_spans):
                continue
            masked_spans.append(span)
            answers.append({'원문': m.group(0), '유형': kind, 'span': span})

    if not answers:
        return text, []

    # span 순서대로 정렬하여 치환
    answers.sort(key=lambda a: a['span'][0])
    pieces = []
    last = 0
    for i, a in enumerate(answers):
        pieces.append(text[last:a['span'][0]])
        pieces.append(f'[___{i+1}___]')
        last = a['span'][1]
    pieces.append(text[last:])
    masked = ''.join(pieces)

    # span 정보는 출력에서 제거
    for a in answers:
        del a['span']
    return masked, answers


def parse_file(p: Path, category: str) -> list:
    fm, body = read_md(p)
    if fm.get('상태') != 'filled':
        return []
    case_number = fm.get('사건번호', p.stem)
    date = fm.get('선고일', '')
    case_name = fm.get('사건명', '')

    # 역추적 메타데이터 빌드
    raw_sources = parse_sources_table(body)
    enriched_sources = []
    for src in raw_sources:
        entry = {'book_name': src['book_name'], 'context_path': src['context_path']}
        page = find_page_in_context(src['context_path'], case_number)
        if page:
            entry['page'] = page
        enriched_sources.append(entry)
    references = {
        'case_stub_link': f'[[{case_number}]]',
        'sources': enriched_sources,
    }

    lines = extract_summary_block(body)
    problems = []
    for idx, para in enumerate(lines):
        if len(para) < MIN_PARAGRAPH_LEN:
            continue
        # 항 접두사 제거 (예: '가.', '[1]')
        clean = re.sub(r'^\s*(?:\[\d+\]|\([가-힣0-9]+\)|[가-힣]\.)\s*', '', para).strip()
        masked, answers = blank_paragraph(clean)
        if not answers:
            continue
        problems.append({
            'id': f'prec-blank-{case_number}-{idx+1}',
            '사건번호': case_number,
            '선고일': date,
            '사건명': case_name,
            '분야': category,
            '소스': str(p.relative_to(Path('H:/내 드라이브'))).replace('\\', '/'),
            '원문': clean,
            '문제': masked,
            '정답': [a['원문'] for a in answers],
            '유형별': [a['유형'] for a in answers],
            '유형': 'BLANK',
            'references': references,
        })
    return problems


def main():
    all_problems = []
    stats = {}
    for sub, cat in (('민법', 'civil'), ('형법', 'criminal'), ('헌법', 'constitutional')):
        d = ROOT / sub
        count = 0
        files = 0
        for f in sorted(d.iterdir()):
            if f.suffix != '.md' or f.name.startswith('_'):
                continue
            items = parse_file(f, cat)
            if items:
                files += 1
            count += len(items)
            all_problems.extend(items)
        stats[sub] = {'files_with_blank': files, 'problems': count}

    OUT_PATH.write_text(
        json.dumps({'generated_at': '2026-04-18', 'version': 1,
                    'stats': stats, 'problems': all_problems},
                   ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print('=== 블랭크 문제 생성 요약 ===')
    for k, v in stats.items():
        print(f'  {k}: 판례 {v["files_with_blank"]}건 → 문항 {v["problems"]}개')
    print(f'총 문항: {len(all_problems)}')
    print(f'저장: {OUT_PATH}')


if __name__ == '__main__':
    main()
