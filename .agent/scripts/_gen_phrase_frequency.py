#!/usr/bin/env python3
"""사례집(사례형) 코퍼스에서 '반복 문구(정형 표현)' 빈도 — 판례번호가 아닌 문구 자체.

목적: (1) 조문/문구 검색기능 보완 인덱스 (2) 답안에 '써야 할 정형구' 보조.
방법: 문장 분리 → 정규화(판례번호·날짜 제거, 甲乙丙→X, 제NNN조→제N조) →
      OCR메타/선택형지문 노이즈 라인 제거 → 반복(3회+) 문구 집계.
분류: 판례 문구 = 정규화 문장이 '판시 어미'로 끝남(…것이다/…보아야 한다/…봄이 상당하다 등).
      사례집·답안 문구 = 그 외 반복 정형구(살피건대/사안의 경우/따라서 …).

코퍼스(사례형만): 01_ocr 중 이름에 '사례' 포함(사례연습·민사사례연습·민소사례·해커스헌법사례)
      + 1·2·3.공법/90.기출/**.md. 선택형(유니온헌법기출·강성민OX·compact OX)·이론서 제외.
출력: 9.작업중/클로드/사례집_문구빈도_2026-07-01.md
주의(#22·#34): 판례 문구는 표기형 근사. 답안 인용 전 원문 대조 필수.
"""
import glob
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'E:\법학볼트'
OCR = os.path.join(ROOT, 'outputs', '01_ocr_llamaparse')
GICHUL = [os.path.join(ROOT, s, '90.기출') for s in ('1.민사', '2.형사', '3.공법')]
OUT = os.path.join(ROOT, 'sync', '_meta', '사례집_문구빈도_2026-07-01.md')

CASE_RE = re.compile(r'\d{2,4}(?:다카|다|도|두|누|므|르|후|헌가|헌바|헌마|헌라|헌나|그|재|모)\d{1,6}')
DATE_RE = re.compile(r'\d{2,4}\s?\.\s?\d{1,2}\s?\.\s?\d{1,2}\s?\.?')
ART_RE = re.compile(r'제\s?\d{1,4}조(?:의\s?\d{1,3})?')
PARTY_RE = re.compile(r'[甲乙丙丁戊己庚辛壬癸]')
MD_RE = re.compile(r'[#>*|`_~\[\]【】「」『』（）()<>ﾠ]')
# OCR 메타데이터 + 선택형 문제 지문 노이즈 (이 패턴 있으면 문장 버림)
NOISE = re.compile(r'(추출엔진|교정상태|출처회차|page ?number|LlamaParse|멀티모달|anchor|tier=|lang=|'
                   r'발문형|정답선지|함정선지|정답\s*[:：]|해설\s*[:：]|다툼이 있는 경우|옳지 ?않은|'
                   r'옳은 ?것|모두 고른|[①②③④⑤⑥⑦⑧⑨]|[ᄀ-ᅵㄱ-ㅎ]\s|주문과 같다|청 ?구 ?취 ?지|'
                   r'tags|교재\s*[:：]|출처\s*[:：]|미교정|요약형|진도별|모의시험|해설 ?년도|제차 변호사|'
                   r'답안지|시험시간|시험 ?종료|수정액|감독|유의사항|정정할|교체 ?요구|회수|기재하여야 하며|\.pdf)')
PANRYE_END = re.compile(r'(것이다|보아야 한다|봄이 상당하다|함이 상당하다|할 수 없다|할 수 있다|'
                        r'하여야 한다|반한다|추정한다|간주한다|보는 것이 상당하다|할 것이다|'
                        r'라 할 것이다|다고 할 것이다|라고 할 것이다|해석하여야 한다)$')
# 답안 정형구 allowlist — 법률 답안에 실제 '써야 할' 표현 마커 포함 문장만
ANSWER_MARK = re.compile(r'(살피건대|생각건대|사안의 경우|사안에서|검토하건대|판단하건대|보건대|'
                         r'문제된다|문제가 된다|쟁점은|성립한다|성립하지|성립요건|인정된다|인정되지|'
                         r'해당한다|해당하지|요건을|요건이|청구할 수 있다|청구권|주장할 수 있|'
                         r'항변|증명책임|입증책임|반환을 청구|손해배상|부당이득|불법행위|채무불이행|'
                         r'취소할 수 있|무효이|대항할 수 없|위법|책임을 진다|배상책임)')
SENT_SPLIT = re.compile(r'(?<=다\.)\s+|(?<=[.!?])\s+|\n+')


def normalize(s):
    s = CASE_RE.sub('', s)
    s = DATE_RE.sub('', s)
    s = ART_RE.sub('제N조', s)
    s = PARTY_RE.sub('X', s)
    s = MD_RE.sub(' ', s)
    s = re.sub(r'\d+', '', s)
    s = re.sub(r'\s+', ' ', s).strip(' .·-—')
    return s


def collect():
    fs = []
    for fp in glob.glob(os.path.join(OCR, '*.md')):
        nm = os.path.basename(fp)
        if '사례' in nm and '목차' not in nm:
            fs.append(fp)
    for d in GICHUL:
        fs += glob.glob(os.path.join(d, '**', '*.md'), recursive=True)
    return fs


freq = Counter()
files = collect()
for fp in files:
    try:
        text = open(fp, encoding='utf-8', errors='ignore').read()
    except OSError:
        continue
    for raw in SENT_SPLIT.split(text):
        if NOISE.search(raw):
            continue
        n = normalize(raw)
        if n.startswith(('제장', '제절', '제관', '제편', '문 ', '사례', '설문')):
            continue
        if 14 <= len(n) <= 110 and n.count(' ') >= 3 and not NOISE.search(n):
            freq[n] += 1

items = [(p, c) for p, c in freq.items() if c >= 3]
panrye = sorted([x for x in items if PANRYE_END.search(x[0]) and '가상' not in x[0]],
                key=lambda x: -x[1])
casebook = sorted([x for x in items if not PANRYE_END.search(x[0]) and ANSWER_MARK.search(x[0])],
                  key=lambda x: -x[1])


def tbl(rows, n):
    out = ['| 순위 | 반복 | 문구(정규화) |', '|---|---|---|']
    for i, (p, c) in enumerate(rows[:n], 1):
        out.append(f'| {i} | {c} | {p} |')
    return out


lines = ['---', 'tags: [사례집, 문구빈도, 정형구, 답안보조]', '생성일: 2026-07-01', '---', '',
         '# 사례집(사례형) 반복 문구 빈도 — 판례 문구 / 답안 문구', '',
         '> [!warning] #22·#34 — 반복 정형 문구. 판례 문구는 표기형 근사이므로 답안 인용 전 원문 대조 필수.',
         '> 코퍼스는 사례형만(선택형·OX 제외). OCR 메타/선택형 지문 노이즈 라인 제거.',
         '',
         f'- 대상 파일 {len(files)} · 후보 문구(3회+) {len(items)} (판례형 {len(panrye)} / 답안형 {len(casebook)})',
         '', '## 판례 문구 상위 60 (판시 정형구 — 답안 인용용)', '']
lines += tbl(panrye, 60)
lines += ['', '## 사례집·답안 문구 상위 60 (구조·해설 정형구)', '']
lines += tbl(casebook, 60)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')

print(f'파일 {len(files)} · 후보문구(3회+) {len(items)} (판례 {len(panrye)}/답안 {len(casebook)})')
print('--- 판례 문구 TOP 12 ---')
for p, c in panrye[:12]:
    print(f'  {c:>3}  {p[:64]}')
print('--- 답안 문구 TOP 12 ---')
for p, c in casebook[:12]:
    print(f'  {c:>3}  {p[:64]}')
print('OUT ->', OUT)
