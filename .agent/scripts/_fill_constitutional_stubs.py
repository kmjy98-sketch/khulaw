#!/usr/bin/env python3
"""헌법재판소 스텁 전용 채움 스크립트.

- `sync/_판례색인/헌법/` 하위 `상태: stub` 파일 대상.
- 국가법령정보센터 API target=detc로 검색·상세 조회.
- 판시사항 + 결정요지 + 참조조문 + 참조판례 삽입.
- 출현 교재 테이블은 보존.
"""
import os
import re
import sys
import time
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

OC = 'km9752'
BASE = 'https://www.law.go.kr/DRF'
ROOT = Path('H:/내 드라이브/sync/_판례색인/헌법')
REPORT_PATH = Path('H:/내 드라이브/.agent/state/precedent_fill_const_2026-04-18.json')

MAX_SEARCH_PAGES = 6
PAGE_SIZE = 50


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


def write_md(p: Path, fm: dict, body: str):
    lines = ['---']
    for k, v in fm.items():
        lines.append(f'{k}: {v}')
    lines.append('---')
    text = '\n'.join(lines) + '\n\n' + body
    p.write_text(text, encoding='utf-8')


def strip_html(s: str) -> str:
    if not s:
        return ''
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'\n{3,}', '\n\n', s)
    s = re.sub(r'[ \t]{2,}', ' ', s)
    return s.strip()


def search_detc(case_number: str) -> dict | None:
    """detc 검색. 사건번호 정확 매칭 항목 반환."""
    for page in range(1, MAX_SEARCH_PAGES + 1):
        try:
            r = requests.get(f'{BASE}/lawSearch.do', params={
                'OC': OC, 'target': 'detc', 'type': 'XML',
                'query': case_number, 'display': PAGE_SIZE, 'page': page,
            }, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f'    search error: {e}')
            return None
        try:
            root = ET.fromstring(r.text)
        except ET.ParseError:
            return None
        items = root.findall('.//Detc')
        if not items:
            return None
        for d in items:
            if (d.findtext('사건번호') or '').strip() == case_number:
                return {
                    'id': d.findtext('헌재결정례일련번호', ''),
                    'date': d.findtext('종국일자', ''),
                    'case_number': d.findtext('사건번호', ''),
                    'case_name': d.findtext('사건명', ''),
                }
        if len(items) < PAGE_SIZE:
            return None
    return None


def get_detc_detail(doc_id: str) -> dict | None:
    try:
        r = requests.get(f'{BASE}/lawService.do', params={
            'OC': OC, 'target': 'detc', 'type': 'XML', 'ID': doc_id,
        }, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f'    detail error: {e}')
        return None
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return None
    return {
        'id': root.findtext('.//헌재결정례일련번호', ''),
        'case_number': root.findtext('.//사건번호', ''),
        'case_name': root.findtext('.//사건명', ''),
        'date': root.findtext('.//종국일자', ''),
        'case_type': root.findtext('.//사건종류명', ''),
        '판시사항': root.findtext('.//판시사항', ''),
        '결정요지': root.findtext('.//결정요지', ''),
        '참조조문': root.findtext('.//참조조문', ''),
        '참조판례': root.findtext('.//참조판례', ''),
        '심판대상조문': root.findtext('.//심판대상조문', ''),
    }


def normalize_date(raw: str) -> str:
    raw = (raw or '').strip()
    if re.match(r'^\d{8}$', raw):
        return f'{raw[:4]}.{int(raw[4:6])}.{int(raw[6:8])}'
    # "2010.04.29" → "2010.4.29"
    m = re.match(r'^(\d{4})\.(\d{1,2})\.(\d{1,2})$', raw)
    if m:
        y, mo, d = m.groups()
        return f'{y}.{int(mo)}.{int(d)}'
    return raw


def build_body(detail: dict, case_number: str, date_iso: str, existing_body: str) -> str:
    case_name = detail.get('case_name', '')
    판시사항 = strip_html(detail.get('판시사항', ''))
    결정요지 = strip_html(detail.get('결정요지', ''))
    참조조문 = strip_html(detail.get('참조조문', ''))
    참조판례 = strip_html(detail.get('참조판례', ''))
    심판대상조문 = strip_html(detail.get('심판대상조문', ''))

    # 출현 교재 이하 보존
    m = re.search(r'^## 출현 교재.*$', existing_body, re.MULTILINE)
    tail = existing_body[m.start():] if m else ''

    title = f'헌재 {date_iso or "?"} {case_number}'

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
    if 결정요지:
        out.append(f'> [!판례] 결정요지 — {case_number}')
        for line in 결정요지.split('\n'):
            line = line.strip()
            if line:
                out.append(f'> {line}')
        out.append('')

    if 심판대상조문:
        out.append('## 심판대상조문')
        out.append('')
        out.append(심판대상조문)
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

    found = search_detc(case_number)
    if not found:
        return {'file': str(p), 'status': 'not_found', 'case': case_number}

    detail = get_detc_detail(found['id'])
    if not detail:
        return {'file': str(p), 'status': 'detail_error', 'case': case_number}

    date_iso = normalize_date(detail.get('date') or found.get('date', ''))

    new_fm = dict(fm)
    tags = new_fm.get('tags', '')
    tags = re.sub(r',\s*스텁\s*\]', ']', tags)
    tags = re.sub(r'\[\s*스텁\s*,?\s*', '[', tags)
    tags = re.sub(r'스텁\s*,?\s*', '', tags)
    new_fm['tags'] = tags
    new_fm['사건번호'] = case_number
    new_fm['선고일'] = date_iso or fm.get('선고일', '(확인 불가)')
    new_fm['법원'] = '헌법재판소'
    if detail.get('case_name'):
        new_fm['사건명'] = detail['case_name']
    if detail.get('case_type'):
        new_fm['사건종류'] = detail['case_type']
    new_fm['헌재결정례일련번호'] = detail.get('id', '')
    new_fm['상태'] = 'filled'

    new_body = build_body(detail, case_number, date_iso, body)
    write_md(p, new_fm, new_body)
    return {'file': str(p), 'status': 'filled', 'case': case_number,
            'doc_id': detail.get('id'), 'date': date_iso}


def main():
    targets = sorted(
        f for f in ROOT.iterdir()
        if f.suffix == '.md' and not f.name.startswith('_')
    )
    print(f'헌법 스텁 후보: {len(targets)}')
    results = []
    counts = {}

    for i, p in enumerate(targets):
        try:
            r = process_file(p)
        except Exception as e:
            r = {'file': str(p), 'status': 'exception', 'error': str(e)}
        counts[r['status']] = counts.get(r['status'], 0) + 1
        results.append(r)
        print(f'  [{i+1:03d}/{len(targets)}] {r["status"]:18s} {p.name}')
        if r['status'] == 'filled':
            time.sleep(0.3)

    REPORT_PATH.write_text(
        json.dumps({'counts': counts, 'results': results}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print('\n=== 요약 ===')
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f'  {k}: {v}')
    print(f'리포트: {REPORT_PATH}')


if __name__ == '__main__':
    main()
