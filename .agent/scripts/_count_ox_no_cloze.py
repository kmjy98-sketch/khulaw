#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""클로즈 없는 OX 카드 집계 (병렬 클로즈 생성 대상 산정)."""
import glob, os, re
from collections import defaultdict

CARD = r"H:\내 드라이브\outputs\02_cards_v37"
tot = defaultdict(lambda: [0, 0])  # book -> [ox_total, ox_no_cloze]

for fp in glob.glob(os.path.join(CARD, "*.md")):
    fn = os.path.basename(fp)
    book = re.split(r"_p\d|_llamaparse", fn)[0]
    try:
        txt = open(fp, encoding="utf-8").read()
    except Exception:
        continue
    for b in re.split(r"(?m)^(?=### )", txt):
        h = b.split("\n", 1)[0]
        if h.startswith("### ") and "[OX" in h:
            tot[book][0] += 1
            if "{{" not in b:
                tot[book][1] += 1

g_t = sum(v[0] for v in tot.values())
g_n = sum(v[1] for v in tot.values())
print(f"OX 카드 총 {g_t}장 / 클로즈 없음 {g_n}장 / 파일(무클로즈 보유) {sum(1 for v in tot.values() if v[1] > 0)}개")
print("책별 무클로즈 OX (많은 순):")
for book, (t, n) in sorted(tot.items(), key=lambda x: -x[1][1]):
    if n > 0:
        print(f"  {book}: OX {t} / 무클로즈 {n}")
