#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OX 병렬 클로즈 전체실행 준비: 무클로즈 OX 보유 파일 선별 → 백업 → 파일목록을 템플릿에 베이크."""
import glob, os, re, json, shutil

CARD = r"H:\내 드라이브\outputs\02_cards_v37"
BK = r"H:\내 드라이브\5.기타\_백업\OX클로즈_2026-06-22"
TEMPLATE = r"H:\내 드라이브\.agent\scripts\_wf_ox_cloze_pilot.js"
OUT = r"H:\내 드라이브\.agent\scripts\_wf_ox_cloze_RUN.js"
PILOT = {"강성민OX3_llamaparse_p001-030_암기장_v37.md", "법조윤리_01.md"}

os.makedirs(BK, exist_ok=True)
targets = []
for fp in glob.glob(os.path.join(CARD, "*.md")):
    fn = os.path.basename(fp)
    if fn in PILOT:
        continue
    try:
        txt = open(fp, encoding="utf-8").read()
    except Exception:
        continue
    miss = 0
    for b in re.split(r"(?m)^(?=### )", txt):
        h = b.split("\n", 1)[0]
        if h.startswith("### ") and "[OX" in h and "{{" not in b:
            miss += 1
    if miss > 0:
        targets.append((fn, miss))

targets.sort(key=lambda x: -x[1])
backed = 0
for fn, _ in targets:
    dest = os.path.join(BK, fn)
    if not os.path.exists(dest):
        shutil.copy2(os.path.join(CARD, fn), dest); backed += 1

files = [fn for fn, _ in targets]
tpl = open(TEMPLATE, encoding="utf-8").read()
items_js = "[\n" + ",\n".join("  { file: %s }" % json.dumps(fn, ensure_ascii=False) for fn in files) + "\n]"
s = tpl.index("const items = [")
e = tpl.index("}))", s) + 3
newblk = "const items = " + items_js + ".map(i => ({ ...i, path: `${CARD}/${i.file}`, bak: `${BK}/${i.file}` }))"
open(OUT, "w", encoding="utf-8").write(tpl[:s] + newblk + tpl[e:])

print(f"OX무클로즈 보유 파일 {len(files)}개 / OX무클로즈 합 {sum(n for _, n in targets)} / 백업 {backed}")
for fn, n in targets[:18]:
    print(f"  {n:4d}  {fn}")
print(f"[written] {OUT}")
