# -*- coding: utf-8 -*-
"""_hl_inventory.py — 일회성(#42). v37 Basic 답면 인벤토리 추출 → 노랑형광 per-card LLM 키워드 슬라이스.
빌더 함수를 import해 want_basic 경로를 그대로 재현, key=md5(_base(dwi))·평문 답면을 수집(중복 제거).
산출: .agent/state/_hl_basic_inventory.jsonl  (각 줄 {k, text})
"""
import os, re, sys, json, hashlib, html, importlib.util

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
spec = importlib.util.spec_from_file_location("bv37", vp(".agent", "scripts", "build_v37_apkg.py"))
B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)

SRC = B.SRC
files = os.listdir(SRC)
minso_cloze_pages = {re.search(r"_p[\d-]+", f).group(0) for f in files
                     if f.startswith("논점민소") and "_cloze" in f and re.search(r"_p[\d-]+", f)}

inv = {}   # key -> plain text
for fn in sorted(files):
    if fn in ("H", "H:") or not fn.endswith(".md") or "_TEMP" in fn:
        continue
    txt = open(os.path.join(SRC, fn), encoding="utf-8").read()
    if txt.count("\n") < 30:
        continue
    if fn.startswith("논점민소") and "_cloze" not in fn:
        pg = re.search(r"_p[\d-]+", fn)
        if pg and pg.group(0) in minso_cloze_pages:
            continue
    grp, subj = B.deck_of(fn)
    if grp is None:
        continue
    for attr, topic, blk in B.blocks_of(txt):
        ap = B.field(blk, ["앞", "앞면"]); dwi = B.field(blk, ["뒤", "뒷면"])
        bk = B.field(blk, ["빈칸"]); tx = B.field(blk, ["Text"])
        cloze_src = next((x for x in (bk, tx, dwi, ap) if x and "{{" in x), "")
        if not cloze_src and "{{" in blk and not (ap and "{{" in ap):
            body = blk.split("\n", 1)[1] if "\n" in blk else ""
            cloze_src = re.sub(r"(?m)^\s*\*{0,2}\s*카드\s*[\w-]*\s*\*{0,2}\s*", "", body).strip()
        head_front = re.sub(r"^\*+\s*카드\s*[\w-]*\s*\*+\s*", "",
                            re.sub(r"^#+\s*\[[^\]]*\]\s*", "", blk.split("\n", 1)[0])).strip()
        want_basic = (not cloze_src and dwi and (ap or head_front)) or \
                     (B.DOUBLE and cloze_src == bk and bk and dwi and "{{" not in dwi)
        if not want_basic:
            continue
        front = B.conv(ap) or B.conv(head_front) or attr
        back = B.conv(dwi, hl=True)
        if not (front and back):
            continue
        base = B._base(dwi)                       # 빌더 lookup 키와 동일 입력
        k = hashlib.md5(base.encode("utf-8")).hexdigest()
        if k not in inv:
            inv[k] = html.unescape(re.sub(r"<[^>]+>", "", base)).strip()  # LLM용 평문

out = vp(".agent", "state", "_hl_basic_inventory.jsonl")
with open(out, "w", encoding="utf-8") as f:
    for k, t in inv.items():
        if 4 <= len(t) <= 600:                    # 너무 짧/긴 답면 제외
            f.write(json.dumps({"k": k, "text": t}, ensure_ascii=False) + "\n")
print("고유 Basic 답면:", len(inv), "→", out)
print("길이 분포: <20자", sum(1 for t in inv.values() if len(t) < 20),
      "/ 20~120", sum(1 for t in inv.values() if 20 <= len(t) <= 120),
      "/ >120", sum(1 for t in inv.values() if len(t) > 120))
