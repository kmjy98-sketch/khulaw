#!/usr/bin/env python3
"""고빈도 판례·조문에 대해 스텁 .md 생성.

- 분야별(민사·형사·헌법) 상위 N건을 각각 폴더에 생성.
- 기존 파일은 덮어쓰지 않음.
- 판시요지/쟁점/결론은 플레이스홀더 ("채움 필요", korean-law-mcp 조회 권고).
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

SRC = 'H:/내 드라이브/.agent/state/references_all_2026-04-18_v2.json'
TEXTBOOK_ROOT = 'H:/내 드라이브/sync/_교재원문'
CASE_OUT_CIVIL = 'H:/내 드라이브/sync/_판례색인/민법'
CASE_OUT_CRIMINAL = 'H:/내 드라이브/sync/_판례색인/형법'
CASE_OUT_CONST = 'H:/내 드라이브/sync/_판례색인/헌법'
STAT_OUT = 'H:/내 드라이브/sync/_조문원문/민법'

TOP_CIVIL_N = 30
TOP_CRIMINAL_N = 30
TOP_CONST_N = 30
TOP_STAT_N = 20

CRIMINAL_RE = re.compile(r'^\d{2,4}도\d{2,6}$')
CONST_RE = re.compile(r'^\d{2,4}헌')
CIVIL_RE = re.compile(r'^\d{2,4}(?:다카|다)\d{2,6}$')


def classify(num: str) -> str:
    if CIVIL_RE.match(num):
        return 'civil'
    if CRIMINAL_RE.match(num):
        return 'criminal'
    if CONST_RE.match(num):
        return 'constitutional'
    return 'other'


with open(SRC, 'r', encoding='utf-8') as f:
    data = json.load(f)

case_agg = defaultdict(lambda: {'count': 0, 'files': [], 'date': None})
statute_agg = defaultdict(lambda: {'count': 0, 'files': []})

for result in data.get('per_file', []):
    fp = result['file']
    try:
        rel = os.path.relpath(fp, TEXTBOOK_ROOT).replace('\\', '/')
    except ValueError:
        rel = fp
    stem = os.path.splitext(os.path.basename(fp))[0]

    for case_num, cnt in result['cases']['frequency'].items():
        case_agg[case_num]['count'] += cnt
        case_agg[case_num]['files'].append((stem, rel, cnt))
    for detail in result['cases']['details']:
        if detail.get('date') and not case_agg[detail['number']]['date']:
            case_agg[detail['number']]['date'] = detail['date']

    for stat_ref, cnt in result['statutes']['frequency'].items():
        statute_agg[stat_ref]['count'] += cnt
        statute_agg[stat_ref]['files'].append((stem, rel, cnt))


CATEGORY_META = {
    'civil': dict(tag='민법', court='대법원', prefix='대판', out=CASE_OUT_CIVIL),
    'criminal': dict(tag='형법', court='대법원', prefix='대판', out=CASE_OUT_CRIMINAL),
    'constitutional': dict(tag='헌법', court='헌법재판소', prefix='헌재', out=CASE_OUT_CONST),
}


def case_stub(num: str, info: dict, cat: str) -> str:
    meta = CATEGORY_META[cat]
    date = info['date']
    date_line = f'선고일: {date}' if date else '선고일: (확인 불가)'
    title = f'{meta["prefix"]} {date} {num}' if date else f'{meta["prefix"]} {num}'
    # dedup by stem (max cnt)
    file_max = {}
    for stem, rel, cnt in info['files']:
        if stem not in file_max or file_max[stem][2] < cnt:
            file_max[stem] = (stem, rel, cnt)
    files = sorted(file_max.values(), key=lambda x: -x[2])[:20]

    lines = [
        '---',
        f'tags: [판례, {meta["tag"]}, 스텁]',
        f'사건번호: {num}',
        date_line,
        f'법원: {meta["court"]}',
        '상태: stub',
        '---',
        '',
        f'# {title}',
        '',
        '> [!판례] 판시요지 (채움 필요)',
        '> (원문은 `korean-law-mcp`의 `search_precedent_tool` / `get_precedent_detail_tool`로 조회 후 삽입)',
        '',
        '## 핵심 쟁점',
        '',
        '- (채움 필요)',
        '',
        '## 결론',
        '',
        '- (채움 필요)',
        '',
        f'## 출현 교재 (상위 {len(files)}건)',
        '',
        '| 교재 파일 | 맥락 경로 | 출현 |',
        '|-----------|-----------|------|',
    ]
    for stem, rel, cnt in files:
        lines.append(f'| [[{stem}]] | `{rel}` | {cnt} |')
    lines += ['', '## 관련 판례', '', '- (채움 필요)']
    return '\n'.join(lines) + '\n'


def statute_stub(ref: str, info: dict) -> tuple[str, str]:
    m = re.match(r'제(\d+)조', ref)
    if not m:
        return None, None
    article = m.group(1)
    fname = f'제{article}조.md'
    file_max = {}
    for stem, rel, cnt in info['files']:
        if stem not in file_max or file_max[stem][2] < cnt:
            file_max[stem] = (stem, rel, cnt)
    files = sorted(file_max.values(), key=lambda x: -x[2])[:20]
    lines = [
        '---',
        'tags: [조문, 민법, 스텁]',
        '법률: 민법',
        f'조문: {article}',
        '상태: stub',
        '---',
        '',
        f'# 제{article}조',
        '',
        f'> [!조문] 민법 제{article}조',
        '> (원문은 `korean-law-mcp`의 `search_law_tool` / `get_law_detail_tool`로 조회 후 삽입)',
        '',
        '## 요건',
        '',
        '- (채움 필요)',
        '',
        '## 관련 조문',
        '',
        '| 조문 | 관계 |',
        '|------|------|',
        '| (채움 필요) | |',
        '',
        f'## 출현 교재 (상위 {len(files)}건)',
        '',
        '| 교재 파일 | 맥락 경로 | 출현 |',
        '|-----------|-----------|------|',
    ]
    for stem, rel, cnt in files:
        lines.append(f'| [[{stem}]] | `{rel}` | {cnt} |')
    return fname, '\n'.join(lines) + '\n'


# 분야별 상위 N 추출
buckets = {'civil': [], 'criminal': [], 'constitutional': []}
for num, info in case_agg.items():
    c = classify(num)
    if c in buckets:
        buckets[c].append((num, info))
for c in buckets:
    buckets[c].sort(key=lambda x: -x[1]['count'])

# 스텁 생성
stats = {}
for cat, N in (('civil', TOP_CIVIL_N), ('criminal', TOP_CRIMINAL_N), ('constitutional', TOP_CONST_N)):
    out_dir = CATEGORY_META[cat]['out']
    os.makedirs(out_dir, exist_ok=True)
    created = 0
    skipped = 0
    for num, info in buckets[cat][:N]:
        safe = re.sub(r'[\\/:*?"<>|]', '_', num)
        path = os.path.join(out_dir, f'{safe}.md')
        if os.path.exists(path):
            skipped += 1
            continue
        with open(path, 'w', encoding='utf-8') as f:
            f.write(case_stub(num, info, cat))
        created += 1
    stats[cat] = (created, skipped, N)

# 조문 스텁
os.makedirs(STAT_OUT, exist_ok=True)
article_agg = defaultdict(lambda: {'count': 0, 'files': []})
for ref, info in statute_agg.items():
    m = re.match(r'제(\d+)조', ref)
    if not m:
        continue
    base = f'제{m.group(1)}조'
    article_agg[base]['count'] += info['count']
    article_agg[base]['files'].extend(info['files'])

top_stats = sorted(article_agg.items(), key=lambda x: -x[1]['count'])[:TOP_STAT_N]
stat_created = 0
stat_skipped = 0
for ref, info in top_stats:
    fname, body = statute_stub(ref, info)
    if not fname:
        continue
    path = os.path.join(STAT_OUT, fname)
    if os.path.exists(path):
        stat_skipped += 1
        continue
    with open(path, 'w', encoding='utf-8') as f:
        f.write(body)
    stat_created += 1

for cat, (c, s, n) in stats.items():
    print(f'[{cat}] 판례 스텁: 생성 {c} / 기존유지 {s} (대상 {n})')
print(f'[statute] 조문 스텁: 생성 {stat_created} / 기존유지 {stat_skipped} (대상 {TOP_STAT_N})')
