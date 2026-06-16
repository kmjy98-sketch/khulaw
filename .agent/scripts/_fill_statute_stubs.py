#!/usr/bin/env python3
"""민법 조문 스텁 채움.

- `sync/_조문원문/민법/` 하위 `상태: stub` 파일 대상.
- 민법 전체를 law.go.kr API로 1회 조회, 조문별 파싱 후 stub에 삽입.
- 각 stub 파일의 '## 출현 교재' 이하 테이블은 보존.
"""
import os
import re
import sys
import json
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path('H:/내 드라이브/sync/_조문원문/민법')
REPORT_PATH = Path('H:/내 드라이브/.agent/state/statute_fill_report_2026-04-18.json')
CIVIL_LAW_ID = '001706'  # 민법


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


def fetch_civil_law() -> dict[str, dict]:
    """민법 전체를 조회해서 {article_num: {...}} 딕셔너리 반환."""
    r = requests.get('https://www.law.go.kr/DRF/lawService.do', params={
        'OC': 'km9752', 'target': 'law', 'type': 'XML', 'ID': CIVIL_LAW_ID,
    }, timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    articles = {}
    for u in root.findall('.//조문단위'):
        num = u.findtext('조문번호', '').strip()
        title = u.findtext('조문제목', '').strip()
        content = (u.findtext('조문내용', '') or '').strip()
        # 실제 조문은 조문제목이 있거나, 내용이 "제N조(" 로 시작
        if not title and not content.startswith(f'제{num}조'):
            continue
        # 첫 항목만 유지 (같은 번호 chapter/section header 무시)
        if num in articles:
            continue
        branch = u.findtext('조문가지번호', '').strip()
        # 항 모으기
        hang_list = []
        for h in u.findall('항'):
            hang_list.append({
                'num': h.findtext('항번호', '').strip(),
                'content': (h.findtext('항내용') or '').strip(),
                '호': [(ho.findtext('호번호', '').strip(),
                       (ho.findtext('호내용') or '').strip())
                       for ho in h.findall('호')],
            })
        articles[num] = {
            'num': num,
            'branch': branch,
            'title': title,
            'content': content,
            '항': hang_list,
        }
    return articles


def build_body(art: dict, existing_body: str) -> str:
    num = art['num']
    title = art['title']
    content = art['content']
    hang_list = art.get('항') or []

    # 출현 교재 이하 보존
    m = re.search(r'^## 출현 교재.*$', existing_body, re.MULTILINE)
    tail = existing_body[m.start():] if m else ''

    out = [f'# 제{num}조' + (f'({title})' if title else ''), '']
    out.append(f'> [!조문] 민법 제{num}조' + (f' ({title})' if title else ''))
    # 조문 본문: 콜아웃 안에 원문 표시
    for line in content.split('\n'):
        line = line.strip()
        if line:
            out.append(f'> {line}')
    if hang_list:
        # 항 번호·내용도 콜아웃에
        for h in hang_list:
            if h['content']:
                out.append(f'>')
                out.append(f'> {h["content"]}')
            for hn, hc in h.get('호', []):
                if hc:
                    out.append(f'> {hc}')
    out.append('')

    if tail:
        out.append(tail)
    return '\n'.join(out) + '\n'


def is_stub(fm: dict) -> bool:
    tags = fm.get('tags', '')
    return '스텁' in tags or fm.get('상태', '') == 'stub'


def process_file(p: Path, articles: dict) -> dict:
    fm, body = read_md(p)
    if not is_stub(fm):
        return {'file': str(p), 'status': 'skip_not_stub'}
    num = fm.get('조문', '').strip()
    if not num:
        m = re.match(r'^제(\d+)조', p.stem)
        if m:
            num = m.group(1)
    if not num:
        return {'file': str(p), 'status': 'skip_no_article'}
    art = articles.get(num)
    if not art:
        return {'file': str(p), 'status': 'not_found', 'article': num}

    new_fm = dict(fm)
    tags = new_fm.get('tags', '')
    tags = re.sub(r',\s*스텁\s*\]', ']', tags)
    tags = re.sub(r'\[\s*스텁\s*,?\s*', '[', tags)
    tags = re.sub(r'스텁\s*,?\s*', '', tags)
    new_fm['tags'] = tags
    new_fm['법률'] = '민법'
    new_fm['조문'] = num
    if art.get('title'):
        new_fm['조문제목'] = art['title']
    new_fm['상태'] = 'filled'

    new_body = build_body(art, body)
    write_md(p, new_fm, new_body)
    return {'file': str(p), 'status': 'filled', 'article': num, 'title': art.get('title', '')}


def main():
    print('민법 전체 조문 로딩 중...')
    articles = fetch_civil_law()
    print(f'  → 조문 {len(articles)}개 확보')

    targets = sorted(f for f in ROOT.iterdir() if f.suffix == '.md' and not f.name.startswith('_'))
    print(f'조문 스텁 후보: {len(targets)}')
    results = []
    counts = {}

    for i, p in enumerate(targets):
        try:
            r = process_file(p, articles)
        except Exception as e:
            r = {'file': str(p), 'status': 'exception', 'error': str(e)}
        counts[r['status']] = counts.get(r['status'], 0) + 1
        results.append(r)
        title_note = f' ({r.get("title","")})' if r.get('title') else ''
        print(f'  [{i+1:02d}/{len(targets)}] {r["status"]:16s} {p.name}{title_note}')

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
