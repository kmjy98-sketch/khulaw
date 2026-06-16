#!/usr/bin/env python3
"""스텁 판례 문서(sync/_판례색인/)를 korean-law-mcp API로 채움.

- frontmatter `상태: stub` + tags 내 `스텁` 검색
- 사건번호로 search_precedent → 판례일련번호 추출
- get_precedent_detail → 판시사항/판결요지/참조조문/참조판례 추가
- frontmatter 갱신(선고일·사건명), 상태 → filled, 스텁 태그 제거
- 출현 교재 테이블은 그대로 보존
"""
import os
import re
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, 'H:/내 드라이브/.agent/skills/korean-law-mcp/src')
os.environ.setdefault('LAW_API_KEY', 'km9752')

from tools import search_precedent, get_precedent_detail

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브/sync/_판례색인')
REPORT_PATH = Path('H:/내 드라이브/.agent/state/precedent_fill_report_2026-04-18.json')

MAX_SEARCH_PAGES = 6
PAGE_SIZE = 50


def read_md(p: Path) -> tuple[dict, str]:
    """frontmatter + body 분리."""
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


def write_md(p: Path, fm: dict, body: str):
    lines = ['---']
    for k, v in fm.items():
        lines.append(f'{k}: {v}')
    lines.append('---')
    text = '\n'.join(lines) + '\n\n' + body
    p.write_text(text, encoding='utf-8')


def strip_html(s: str) -> str:
    """간단한 HTML 태그 제거 (API는 <br/> 등 포함)."""
    if not s:
        return ''
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    s = re.sub(r'[ \t]{2,}', ' ', s)
    return s.strip()


def find_precedent(case_number: str) -> dict | None:
    """사건번호 정확 매칭 검색."""
    for page in range(1, MAX_SEARCH_PAGES + 1):
        r = search_precedent(query=case_number, page=page, page_size=PAGE_SIZE)
        if r.get('error') or not r.get('precedents'):
            break
        for p in r['precedents']:
            if p.get('사건번호', '').strip() == case_number:
                return p
        # 결과가 page_size보다 작으면 더 없는 것
        if len(r['precedents']) < PAGE_SIZE:
            break
    return None


def build_body(detail: dict, case_number: str, date_iso: str, court: str,
               existing_body: str) -> str:
    """새 본문 생성. 기존 '## 출현 교재' 이하 테이블 보존."""
    case_name = detail.get('사건명', '')
    판시사항 = strip_html(detail.get('판시사항', ''))
    판결요지 = strip_html(detail.get('판결요지', ''))
    참조조문 = strip_html(detail.get('참조조문', ''))
    참조판례 = strip_html(detail.get('참조판례', ''))

    # 기존 본문에서 "## 출현 교재" 이하 부분 추출
    m = re.search(r'^## 출현 교재.*$', existing_body, re.MULTILINE)
    if m:
        tail = existing_body[m.start():]
    else:
        tail = ''

    title_date = date_iso if date_iso else '?'
    title = f'{("헌재" if court == "헌법재판소" else "대판")} {title_date} {case_number}'

    out = [f'# {title}']
    if case_name:
        out.append(f'**사건명**: {case_name}')
    out.append('')

    if 판시사항:
        out.append(f'> [!판례] 판시사항 — {case_number}')
        for line in 판시사항.split('\n'):
            line = line.strip()
            if line:
                out.append(f'> {line}')
        out.append('')
    if 판결요지:
        out.append(f'> [!판례] 판결요지 — {case_number}')
        for line in 판결요지.split('\n'):
            line = line.strip()
            if line:
                out.append(f'> {line}')
        out.append('')

    if 참조조문:
        out.append('## 참조조문')
        out.append('')
        out.append(참조조문)
        out.append('')
    if 참조판례:
        out.append('## 참조판례')
        out.append('')
        out.append(참조판례)
        out.append('')

    if tail:
        out.append(tail)
    return '\n'.join(out) + '\n'


def is_stub(fm: dict) -> bool:
    tags = fm.get('tags', '')
    return '스텁' in tags or fm.get('상태', '') == 'stub'


def process_file(p: Path) -> dict:
    fm, body = read_md(p)
    if not is_stub(fm):
        return {'file': str(p), 'status': 'skip_not_stub'}
    case_number = fm.get('사건번호', '').strip()
    if not case_number:
        return {'file': str(p), 'status': 'skip_no_case_number'}

    prec = find_precedent(case_number)
    if not prec:
        return {'file': str(p), 'status': 'not_found', 'case': case_number}

    prec_id = prec.get('판례일련번호', '')
    if not prec_id:
        return {'file': str(p), 'status': 'no_id', 'case': case_number}

    detail = get_precedent_detail(prec_id)
    if detail.get('error'):
        return {'file': str(p), 'status': 'detail_error', 'error': detail['error']}

    # 날짜 ISO 변환 (YYYYMMDD → YYYY.MM.DD)
    raw_date = detail.get('선고일자', prec.get('선고일자', ''))
    if re.match(r'^\d{8}$', raw_date):
        date_iso = f'{raw_date[:4]}.{int(raw_date[4:6])}.{int(raw_date[6:8])}'
    else:
        date_iso = raw_date

    court = detail.get('법원명', prec.get('법원명', ''))
    category = '헌법' if court == '헌법재판소' else ('형법' if '형' in detail.get('사건종류명', '') else '민법')

    # frontmatter 갱신
    new_fm = dict(fm)
    # 스텁 태그 제거
    tags = new_fm.get('tags', '')
    tags = re.sub(r',\s*스텁\s*\]', ']', tags)
    tags = re.sub(r'\[\s*스텁\s*,?\s*', '[', tags)
    tags = re.sub(r'스텁\s*,?\s*', '', tags)
    new_fm['tags'] = tags
    new_fm['사건번호'] = case_number
    new_fm['선고일'] = date_iso or fm.get('선고일', '(확인 불가)')
    new_fm['법원'] = court or fm.get('법원', '')
    if detail.get('사건명'):
        new_fm['사건명'] = detail['사건명']
    new_fm['판례일련번호'] = prec_id
    new_fm['상태'] = 'filled'

    new_body = build_body(detail, case_number, date_iso, court, body)
    write_md(p, new_fm, new_body)
    return {'file': str(p), 'status': 'filled', 'case': case_number,
            'precedent_id': prec_id, 'date': date_iso}


def main():
    # 대상 수집: 판례색인/{민법|형법|헌법}/*.md (밑줄 시작 제외)
    targets = []
    for sub in ('민법', '형법', '헌법'):
        d = ROOT / sub
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix == '.md' and not f.name.startswith('_'):
                targets.append(f)

    print(f'대상 스텁 후보: {len(targets)}')
    results = []
    counts = {'filled': 0, 'not_found': 0, 'no_id': 0, 'skip_not_stub': 0,
              'skip_no_case_number': 0, 'detail_error': 0}

    for i, p in enumerate(targets):
        try:
            r = process_file(p)
        except Exception as e:
            r = {'file': str(p), 'status': 'exception', 'error': str(e)}
            counts['detail_error'] = counts.get('detail_error', 0) + 1
        counts[r['status']] = counts.get(r['status'], 0) + 1
        results.append(r)
        short = p.name
        print(f'  [{i+1:03d}/{len(targets)}] {r["status"]:20s} {short}')
        # 가벼운 예의성 딜레이
        if r['status'] == 'filled':
            time.sleep(0.3)

    # 리포트
    REPORT_PATH.write_text(
        json.dumps({'counts': counts, 'results': results}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print('\n=== 요약 ===')
    for k, v in counts.items():
        if v:
            print(f'  {k}: {v}')
    print(f'리포트: {REPORT_PATH}')


if __name__ == '__main__':
    main()
