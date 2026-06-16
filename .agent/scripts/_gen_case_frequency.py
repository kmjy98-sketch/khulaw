#!/usr/bin/env python3
"""references_all_*.json을 읽어 민사/형사/헌법 빈도표 생성.

출력:
- sync/_판례색인/_고빈도_판례_리스트.md (민사 상위 + 조문 상위)
- sync/_판례색인/_고빈도_형사판례.md
- sync/_판례색인/_고빈도_헌법판례.md
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

SRC = 'H:/내 드라이브/.agent/state/references_all_2026-04-18_v2.json'
OUT_DIR = 'H:/내 드라이브/sync/_판례색인'
TEXTBOOK_ROOT = 'H:/내 드라이브/sync/_교재원문'

CRIMINAL_RE = re.compile(r'^\d{2,4}도\d{2,6}$')
CONSTITUTIONAL_RE = re.compile(r'^\d{2,4}헌')
CIVIL_RE = re.compile(r'^\d{2,4}(?:다카|다)\d{2,6}$')

with open(SRC, 'r', encoding='utf-8') as f:
    data = json.load(f)

case_agg = defaultdict(lambda: {'count': 0, 'files': Counter(), 'date': None})
statute_agg = defaultdict(lambda: {'count': 0, 'files': Counter()})

for result in data.get('per_file', []):
    fp = result['file']
    try:
        rel = os.path.relpath(fp, TEXTBOOK_ROOT).replace('\\', '/')
    except ValueError:
        rel = fp
    parts = rel.split('/')
    book = parts[1] if len(parts) > 2 else 'unknown'

    for case_num, cnt in result['cases']['frequency'].items():
        case_agg[case_num]['count'] += cnt
        case_agg[case_num]['files'][book] += cnt
    for detail in result['cases']['details']:
        if detail.get('date') and not case_agg[detail['number']]['date']:
            case_agg[detail['number']]['date'] = detail['date']

    for stat_ref, cnt in result['statutes']['frequency'].items():
        statute_agg[stat_ref]['count'] += cnt
        statute_agg[stat_ref]['files'][book] += cnt


def classify(num: str) -> str:
    if CIVIL_RE.match(num):
        return 'civil'
    if CRIMINAL_RE.match(num):
        return 'criminal'
    if CONSTITUTIONAL_RE.match(num):
        return 'constitutional'
    return 'other'


civil_cases = []
criminal_cases = []
const_cases = []
other_cases = []
for num, info in case_agg.items():
    c = classify(num)
    (civil_cases if c == 'civil' else
     criminal_cases if c == 'criminal' else
     const_cases if c == 'constitutional' else
     other_cases).append((num, info))

for L in (civil_cases, criminal_cases, const_cases, other_cases):
    L.sort(key=lambda x: -x[1]['count'])


def top_table(items, n=100, header='| 순위 | 사건번호 | 선고일 | 총 출현 | 주요 교재(횟수) |', sep='|------|----------|--------|---------|-----------------|'):
    lines = [header, sep]
    for i, (num, info) in enumerate(items[:n], 1):
        date = info['date'] or '-'
        top_books = ', '.join(f'{b}({c})' for b, c in info['files'].most_common(3))
        lines.append(f'| {i} | [[{num}]] | {date} | {info["count"]} | {top_books} |')
    return lines


os.makedirs(OUT_DIR, exist_ok=True)

# 민사 + 조문 통합
out_civil = [
    '---',
    'tags: [판례색인, 집계, 민사]',
    '생성일: 2026-04-18',
    '범위: sync/_교재원문/ 전체 (1112파일)',
    '---',
    '',
    '# 고빈도 판례·조문 리스트 (민사 중심)',
    '',
    f'- 전체 교재 파일: **{data["total_files"]}**',
    f'- 고유 판례(전체): **{len(case_agg)}**',
    f'  - 민사(다/다카): **{len(civil_cases)}**',
    f'  - 형사(도): **{len(criminal_cases)}**',
    f'  - 헌법(헌가/헌바/헌마/헌라/헌나): **{len(const_cases)}**',
    f'  - 기타(두/누/마/허/재/그/모 등): **{len(other_cases)}**',
    f'- 고유 조문: **{len(statute_agg)}**',
    '- 집계 시각: 2026-04-18',
    '- 원본 리포트: `.agent/state/references_all_2026-04-18_v2.json`',
    '',
    '> [!note] 분야별 세부 리스트',
    '> - 형사: [[_고빈도_형사판례]]',
    '> - 헌법: [[_고빈도_헌법판례]]',
    '',
    '## 민사 판례 상위 100',
    '',
]
out_civil += top_table(civil_cases, n=100)

top_statutes = sorted(statute_agg.items(), key=lambda x: -x[1]['count'])[:50]
out_civil += [
    '',
    '## 조문 참조 상위 50',
    '',
    '| 순위 | 조문 | 총 출현 | 주요 교재(횟수) |',
    '|------|------|---------|-----------------|',
]
for i, (ref, info) in enumerate(top_statutes, 1):
    m = re.search(r'제(\d+)조', ref)
    wiki = f'[[{ref.split()[0]}]]' if m else ref
    top_books = ', '.join(f'{b}({c})' for b, c in info['files'].most_common(3))
    out_civil.append(f'| {i} | {wiki} | {info["count"]} | {top_books} |')

with open(os.path.join(OUT_DIR, '_고빈도_판례_리스트.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_civil) + '\n')

# 형사
out_criminal = [
    '---',
    'tags: [판례색인, 집계, 형사]',
    '생성일: 2026-04-18',
    '---',
    '',
    '# 고빈도 판례 리스트 (형사)',
    '',
    f'- 고유 형사 판례: **{len(criminal_cases)}**',
    '',
    '## 형사 판례 상위 100',
    '',
]
out_criminal += top_table(criminal_cases, n=100)
with open(os.path.join(OUT_DIR, '_고빈도_형사판례.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_criminal) + '\n')

# 헌법
out_const = [
    '---',
    'tags: [판례색인, 집계, 헌법]',
    '생성일: 2026-04-18',
    '---',
    '',
    '# 고빈도 판례 리스트 (헌법)',
    '',
    f'- 고유 헌법 판례: **{len(const_cases)}**',
    '',
    '## 헌법 판례 상위 100',
    '',
]
out_const += top_table(const_cases, n=100)
with open(os.path.join(OUT_DIR, '_고빈도_헌법판례.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_const) + '\n')

print(f'민사 상위 100 + 조문 상위 50 → _고빈도_판례_리스트.md ({len(civil_cases)} civil)')
print(f'형사 상위 100 → _고빈도_형사판례.md ({len(criminal_cases)} criminal)')
print(f'헌법 상위 100 → _고빈도_헌법판례.md ({len(const_cases)} constitutional)')
print(f'기타(두/누/마/허/재/그/모): {len(other_cases)}')
