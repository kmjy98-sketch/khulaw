#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WF2 실행 스크립트 생성: 템플릿(_wf2_cloze_fix.js)에 대상목록·플래그를 주입.
모드: pilot | full | pass2 | pass2pilot
- pass2*: const PASS2 = true 주입 → 앞면 `( )`+키워드 → 클로즈 완성문(중복) 규칙 활성.
"""
import json, os, sys

MODE = sys.argv[1] if len(sys.argv) > 1 else "full"
TEMPLATE = r"H:\내 드라이브\.agent\scripts\_wf2_cloze_fix.js"
ARGS = r"H:\내 드라이브\.agent\state\_wf2_args.json"
OUTMAP = {
    "pilot": r"H:\내 드라이브\.agent\scripts\_wf2_pilot_RUN.js",
    "full": r"H:\내 드라이브\.agent\scripts\_wf2_cloze_fix_RUN.js",
    "pass2": r"H:\내 드라이브\.agent\scripts\_wf2_pass2_RUN.js",
    "pass2pilot": r"H:\내 드라이브\.agent\scripts\_wf2_pass2_pilot_RUN.js",
}
OUT = OUTMAP[MODE]

PILOT = {
    "compact형총OX_llamaparse_p211-240_암기장_v37.md", "강성민OX2_llamaparse_p061-086_암기장_v37.md",
    "신민사법선택형_가족법_llamaparse_p061-090_암기장_v37.md", "논점민소_p421-450_cloze_v37.md",
    "민사사례연습1_p181-210_v37.md", "신민사법선택형_물권_llamaparse_p061-090_암기장_v37.md",
    "반반형법_llamaparse_p181-210_암기장_v37.md", "쟁점노트_재산법_llamaparse_p031-060_암기장_v37.md",
}
PASS2PILOT = {"신민사법선택형_가족법_llamaparse_p061-090_암기장_v37.md", "논점민소_p421-450_cloze_v37.md"}

with open(TEMPLATE, encoding="utf-8") as f:
    tpl = f.read()
with open(ARGS, encoding="utf-8") as f:
    a = json.load(f)
allitems = a["items"]

if MODE == "pilot":
    items = [i for i in allitems if i["file"] in PILOT]; sample = len(items)
elif MODE == "pass2pilot":
    items = [i for i in allitems if i["file"] in PASS2PILOT]; sample = len(items)
elif MODE == "pass2":
    items = [i for i in allitems if i["file"] not in PASS2PILOT]; sample = max(12, len(items) // 10)
else:  # full
    items = [i for i in allitems if i["file"] not in PILOT]; sample = max(15, len(items) // 12)

is_pass2 = MODE.startswith("pass2")
inj = (f"const items = {json.dumps(items, ensure_ascii=False)}\n"
       f"const SAMPLE = {sample}\n"
       f"const PASS2 = {'true' if is_pass2 else 'false'}")
old = "const items = (args && args.items) || []\nconst SAMPLE = (args && args.verify_sample) || 0"
assert old in tpl, "템플릿 items/SAMPLE 선언 못 찾음"
with open(OUT, "w", encoding="utf-8") as f:
    f.write(tpl.replace(old, inj))

print(f"MODE={MODE} items={len(items)} SAMPLE={sample} PASS2={is_pass2}")
print(f"[written] {OUT}")
