#!/usr/bin/env python3
"""사례집(casebook) 말뭉치만 스코프한 조문·판례 출현빈도 집계.

대상 = 이미 OCR된 '사례집'만:
  (A) outputs/01_ocr_llamaparse/ 중 파일명에 '사례' 또는 '기출' 포함
      (민사사례연습1 / 사례연습_* / 민소사례 / 해커스헌법사례 / 유니온헌법기출)
  (B) 1.민사|2.형사|3.공법 / 기출 / **.md  (진급시험·변시모의 기록형 등 기출 사례형)
교재(이론서·선택형OX)는 제외한다.

주의(#22): 사례집 내 출현빈도이며, 사례형 출제·해설에서의 등장이므로
'출제빈도' 근사치로 볼 수 있으나 확정 라벨('빈출')로 전용하지 않는다.

출력: 9.작업중/클로드/사례집_말뭉치_빈도_2026-07-01.md
"""
import glob
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'E:\법학볼트'
OCR = os.path.join(ROOT, 'outputs', '01_ocr_llamaparse')
GICHUL = [os.path.join(ROOT, s, '기출') for s in ('1.민사', '2.형사', '3.공법')]
OUT = os.path.join(ROOT, 'sync', '_meta', '사례집_말뭉치_빈도_2026-07-01.md')

CASE_RE = re.compile(r'(\d{2,4})(다카|다|도|두|누|므|르|후|헌가|헌바|헌마|헌라|헌나)(\d{1,6})')
ART_RE = re.compile(r'제\s?(\d{1,4})조(?:의\s?(\d{1,3}))?')
CIVIL, CRIM, CONST = ('다카', '다'), ('도',), ('헌가', '헌바', '헌마', '헌라', '헌나')


def collect_files():
    files = []
    for fp in glob.glob(os.path.join(OCR, '*.md')):
        nm = os.path.basename(fp)
        if ('사례' in nm or '기출' in nm) and '목차' not in nm:
            files.append(('사례집(OCR)', fp))
    for d in GICHUL:
        for fp in glob.glob(os.path.join(d, '**', '*.md'), recursive=True):
            files.append(('기출(기출)', fp))
    return files


case_cnt, case_book, case_kind = Counter(), defaultdict(Counter), {}
art_cnt, art_book = Counter(), defaultdict(Counter)
src_count = Counter()
included = []

for tag, fp in collect_files():
    src_count[tag] += 1
    included.append((tag, os.path.relpath(fp, ROOT)))
    nm = os.path.basename(fp)
    book = re.split(r'_llamaparse|_p\d', nm)[0]
    try:
        text = open(fp, encoding='utf-8', errors='ignore').read()
    except OSError:
        continue
    for m in CASE_RE.finditer(text):
        num = m.group(1) + m.group(2) + m.group(3)
        case_cnt[num] += 1
        case_book[num][book] += 1
        case_kind[num] = m.group(2)
    for m in ART_RE.finditer(text):
        art = '제' + m.group(1) + '조' + ('의' + m.group(2) if m.group(2) else '')
        art_cnt[art] += 1
        art_book[art][book] += 1


def bucket(k):
    return 'civil' if k in CIVIL else 'crim' if k in CRIM else 'const' if k in CONST else 'other'


def sub(b):
    L = [(n, c) for n, c in case_cnt.items() if bucket(case_kind[n]) == b]
    L.sort(key=lambda x: -x[1])
    return L


civil, crim, const = sub('civil'), sub('crim'), sub('const')
arts = sorted(art_cnt.items(), key=lambda x: -x[1])


def tbl(items, n):
    out = ['| 순위 | 사건번호 | 출현 | 주요 사례집(횟수) |', '|---|---|---|---|']
    for i, (num, c) in enumerate(items[:n], 1):
        bk = ', '.join(f'{b}({k})' for b, k in case_book[num].most_common(3))
        out.append(f'| {i} | {num} | {c} | {bk} |')
    return out


lines = ['---', 'tags: [사례집, 말뭉치, 출현빈도, 출제근사]', '생성일: 2026-07-01', '---', '',
         '# 사례집 말뭉치 조문·판례 출현빈도', '',
         '> [!warning] #22 — 사례집 내 출현빈도(출제·해설 등장). 출제빈도 근사치이나 "빈출" 확정 라벨 전용 금지.',
         '',
         f'- 포함 파일: **{len(included)}** ('
         + ', '.join(f'{k} {v}' for k, v in src_count.items()) + ')',
         f'- 고유 판례: **{len(case_cnt)}** (민사 {len(civil)}·형사 {len(crim)}·헌법 {len(const)}) / 고유 조문: **{len(art_cnt)}**',
         '', '## 민사 판례 상위 60', '']
lines += tbl(civil, 60)
lines += ['', '## 형사 판례 상위 40', '']
lines += tbl(crim, 40)
lines += ['', '## 헌법 판례 상위 40', '']
lines += tbl(const, 40)
lines += ['', '## 조문 상위 50', '', '| 순위 | 조문 | 출현 | 주요 사례집 |', '|---|---|---|---|']
for i, (a, c) in enumerate(arts[:50], 1):
    bk = ', '.join(f'{b}({k})' for b, k in art_book[a].most_common(3))
    lines.append(f'| {i} | {a} | {c} | {bk} |')
lines += ['', '## 포함 파일 전체(스코프 확인)', '']
for tag, rel in sorted(included):
    lines.append(f'- [{tag}] {rel}')

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')

print('사례집 파일:', dict(src_count), '합계', len(included))
print(f'판례 {len(case_cnt)} (민{len(civil)}/형{len(crim)}/헌{len(const)}) 조문 {len(art_cnt)}')
print('TOP 민사:', ', '.join(f'{n}:{c}' for n, c in civil[:8]))
print('TOP 형사:', ', '.join(f'{n}:{c}' for n, c in crim[:6]))
print('TOP 조문:', ', '.join(f'{a}:{c}' for a, c in arts[:8]))
print('OUT ->', OUT)
