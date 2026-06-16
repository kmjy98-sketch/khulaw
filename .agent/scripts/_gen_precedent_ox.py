#!/usr/bin/env python3
"""채운 판례에서 OX 문제 자동 생성.

- `판시사항` 내 '여부 (적극)/(소극)' 패턴을 OX 문제로 변환.
- 적극 = O, 소극 = X, 한정 적극 = △(O에 가까움).
- 문제 텍스트: '여부 (X)' 제거, 평서문 완성형으로 변환.
- 결과: `.agent/state/precedent_problems_ox_2026-04-18.json`
  각 문항: {id, 사건번호, 선고일, 분야, 소스경로, 문제, 정답, 해설_요지, references}
- references: {case_stub_link, sources: [{book_name, context_path, page?}]}
"""
import re
import sys
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브/sync/_백업/교재원문_문서_백업_2026-05-22/_판례색인')
TEXTBOOK_ROOT = Path('H:/내 드라이브/sync/_백업/교재원문_문서_백업_2026-05-22/_교재원문')
OUT_PATH = Path('H:/내 드라이브/.agent/state/precedent_problems_ox_2026-04-18.json')

# 페이지 마커 패턴: [p.123], p.123, P.123 (단어 경계 확인)
PAGE_MARKER_RE = re.compile(
    r'\[p\.\s*(\d+)\]'          # [p.123]
    r'|(?<![A-Za-z])p\.\s*(\d+)'  # p.123 (앞에 알파벳 없음)
    r'|(?<![A-Za-z])P\.\s*(\d+)'  # P.123
)
PAGE_WINDOW = 200  # 판례번호 전후 탐색 범위(문자 수)

VERDICT_RE = re.compile(r'여부\s*\(\s*(한정\s*적극|한정\s*소극|적극|소극)\s*\)')


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
    """컨텍스트 파일에서 판례번호 주변 페이지 마커를 탐색해 'p.N' 반환. 없으면 ''."""
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


def extract_issue_block(body: str) -> list[str]:
    """판시사항 콜아웃 블록의 각 줄 반환(> 접두사 제거, 항번호 '가.'/'[1]' 유지)."""
    lines = []
    in_block = False
    for line in body.split('\n'):
        if line.strip().startswith('> [!판례] 판시사항'):
            in_block = True
            continue
        if in_block:
            if line.strip().startswith('> [!판례]'):
                break
            if line.strip() == '' or not line.strip().startswith('>'):
                if line.strip() == '':
                    continue
                break
            lines.append(line.strip().lstrip('>').strip())
    return lines


def to_statement(issue_line: str) -> str | None:
    """판시사항 한 줄 → '옳/그름' 판단 가능한 평서문.

    예: '부당이득반환의무의 지체책임 발생시기' → None (질문 자체는 사실 묻기용).
    예: 'X가 Y에 해당하는지 여부 (소극)' → 'X는 Y에 해당한다' (정답 X).
    """
    m = VERDICT_RE.search(issue_line)
    if not m:
        return None
    # 항 접두사 제거: [1], [2], 가., 나., (1), (2)
    text = re.sub(r'^\s*(?:\[\d+\]|\([가-힣0-9]+\)|[가-힣]\.)\s*', '', issue_line)
    # 여부(...) 및 그 앞뒤 공백/한정어 제거
    # 일반 패턴: "...하는지 여부 (적극)" / "...인지 여부 (소극)" / "...에 해당하는지 여부 (한정 적극)"
    text = VERDICT_RE.sub('', text).strip()
    # 끝의 '~하는지'/'인지'를 '~한다'/'이다'로 변환
    text = re.sub(r'하는지$', '한다', text)
    text = re.sub(r'되는지$', '된다', text)
    text = re.sub(r'(이|인)지$', r'\1다' if False else '이다', text)
    text = re.sub(r'\(이하\s+[^)]+\)', '', text)
    text = text.strip().rstrip(',')
    # 끝이 '한다/된다/이다'로 끝나지 않으면 '가 맞다' 첨가 피함
    if not re.search(r'(한다|된다|이다|다)\.?$', text):
        text = text.rstrip('.') + '인지의 문제(판례의 태도는?)'
    if len(text) < 8:
        return None
    return text


def verdict_to_answer(v: str) -> str:
    v = re.sub(r'\s+', '', v)
    return {'적극': 'O', '소극': 'X', '한정적극': '△', '한정소극': '△'}.get(v, '?')


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

    issues = extract_issue_block(body)
    problems = []
    for idx, line in enumerate(issues):
        m = VERDICT_RE.search(line)
        if not m:
            continue
        stmt = to_statement(line)
        if not stmt:
            continue
        verdict = m.group(1)
        ans = verdict_to_answer(verdict)
        problems.append({
            'id': f'prec-ox-{case_number}-{idx+1}',
            '사건번호': case_number,
            '선고일': date,
            '사건명': case_name,
            '분야': category,
            '소스': str(p.relative_to(Path('H:/내 드라이브'))).replace('\\', '/'),
            '문제_원문': line,
            '문제': stmt,
            '정답': ans,
            '원판정': verdict,
            '유형': 'OX',
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
        stats[sub] = {'files_with_ox': files, 'problems': count}

    OUT_PATH.write_text(
        json.dumps({'generated_at': '2026-04-18', 'version': 1,
                    'stats': stats, 'problems': all_problems},
                   ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print('=== OX 문제 생성 요약 ===')
    for k, v in stats.items():
        print(f'  {k}: 판례 {v["files_with_ox"]}건 → 문항 {v["problems"]}개')
    print(f'총 문항: {len(all_problems)}')
    print(f'저장: {OUT_PATH}')


if __name__ == '__main__':
    main()
