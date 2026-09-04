#!/usr/bin/env python3
"""outputs/01_ocr_llamaparse/ 의 OCR 마크다운에서 조문·판례 '출현빈도'를 직접 집계.

주의(#22): 산출은 '교재·자료 내 출현빈도'(corpus occurrence)일 뿐 '출제빈도'가 아니다.
학습 우선순위의 참고 신호로만 사용하고 '빈출' 라벨로 전용하지 않는다.
현 OCR 코퍼스는 민사(재산법) 중심이므로 결과도 민사에 편중된다.

입력: E:/법학볼트/outputs/01_ocr_llamaparse/*.md
출력: E:/법학볼트/9.작업중/클로드/조문판례_출현빈도_OCR_2026-07-01.md
"""
import glob
import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

OCR_DIR = r'E:\법학볼트\outputs\01_ocr_llamaparse'
OUT = r'E:\법학볼트\9.작업중/클로드\조문판례_출현빈도_OCR_2026-07-01.md'

# 사건번호: 연도(2~4자리)+부호(대법/헌재 계열)+일련번호
CASE_RE = re.compile(r'(\d{2,4})(다카|다|도|두|누|므|르|후|헌가|헌바|헌마|헌라|헌나)(\d{1,6})')
# 조문: 제NNN조(의N)  — 코퍼스 민사중심이라 법명 미표기시 대개 민법
ART_RE = re.compile(r'제\s?(\d{1,4})조(?:의\s?(\d{1,3}))?')

CIVIL = ('다카', '다')
CRIM = ('도',)
CONST = ('헌가', '헌바', '헌마', '헌라', '헌나')

case_cnt = Counter()
case_book = defaultdict(Counter)
art_cnt = Counter()
art_book = defaultdict(Counter)
case_kind = {}

files = sorted(glob.glob(os.path.join(OCR_DIR, '*.md')))
for fp in files:
    base = os.path.basename(fp)
    m = re.match(r'(.+?)_llamaparse', base)
    book = m.group(1) if m else base
    try:
        text = open(fp, encoding='utf-8', errors='ignore').read()
    except OSError:
        continue
    for mm in CASE_RE.finditer(text):
        y, kind, ser = mm.group(1), mm.group(2), mm.group(3)
        num = y + kind + ser
        case_cnt[num] += 1
        case_book[num][book] += 1
        case_kind[num] = kind
    for mm in ART_RE.finditer(text):
        art = '제' + mm.group(1) + '조' + ('의' + mm.group(2) if mm.group(2) else '')
        art_cnt[art] += 1
        art_book[art][book] += 1


def bucket(kind):
    if kind in CIVIL:
        return 'civil'
    if kind in CRIM:
        return 'criminal'
    if kind in CONST:
        return 'const'
    return 'other'


civil = [(n, c) for n, c in case_cnt.items() if bucket(case_kind[n]) == 'civil']
crim = [(n, c) for n, c in case_cnt.items() if bucket(case_kind[n]) == 'criminal']
const = [(n, c) for n, c in case_cnt.items() if bucket(case_kind[n]) == 'const']
for L in (civil, crim, const):
    L.sort(key=lambda x: -x[1])
arts = sorted(art_cnt.items(), key=lambda x: -x[1])


def table(items, n):
    out = ['| 순위 | 사건번호 | 출현 | 주요 교재(횟수) |', '|---|---|---|---|']
    for i, (num, c) in enumerate(items[:n], 1):
        books = ', '.join(f'{b}({k})' for b, k in case_book[num].most_common(3))
        out.append(f'| {i} | {num} | {c} | {books} |')
    return out


lines = [
    '---',
    'tags: [출현빈도, 집계, OCR코퍼스, 민사중심]',
    '생성일: 2026-07-01',
    '범위: outputs/01_ocr_llamaparse/ (%d 파일)' % len(files),
    '---',
    '',
    '# 조문·판례 출현빈도 (OCR 코퍼스 직접 집계)',
    '',
    '> [!warning] #22 라벨 제한',
    "> 아래 수치는 **교재·자료 내 출현빈도**(corpus occurrence)이며 **출제빈도가 아니다.**",
    '> 학습 우선순위의 참고 신호로만 쓰고, 소스 표지 없는 "빈출" 라벨로 전용하지 않는다.',
    '> 현 코퍼스는 민사(재산법) 중심이라 형사·헌법 표본은 얕다.',
    '',
    f'- OCR 파일: **{len(files)}**',
    f'- 고유 판례: **{len(case_cnt)}** (민사 {len(civil)} / 형사 {len(crim)} / 헌법 {len(const)})',
    f'- 고유 조문(제N조): **{len(art_cnt)}**',
    '',
    '## 민사 판례 출현 상위 80',
    '',
]
lines += table(civil, 80)
lines += ['', '## 형사 판례 출현 상위 40', '']
lines += table(crim, 40)
lines += ['', '## 헌법 판례 출현 상위 40', '']
lines += table(const, 40)
lines += ['', '## 조문(제N조) 출현 상위 60', '',
          '| 순위 | 조문 | 출현 | 주요 교재(횟수) |', '|---|---|---|---|']
for i, (art, c) in enumerate(arts[:60], 1):
    books = ', '.join(f'{b}({k})' for b, k in art_book[art].most_common(3))
    lines.append(f'| {i} | {art} | {c} | {books} |')

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')

print(f'files={len(files)} cases={len(case_cnt)} (civil={len(civil)} crim={len(crim)} const={len(const)}) arts={len(art_cnt)}')
print('TOP civil:', ', '.join(f'{n}:{c}' for n, c in civil[:8]))
print('TOP arts :', ', '.join(f'{a}:{c}' for a, c in arts[:8]))
print('OUT ->', OUT)
