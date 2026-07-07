#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""안전 마커 정규화: 카드 파일의 전각괄호 클로즈 【　X　】 → {{X}} (빌더는 {{}}만 지원).
- 찌라시 제외(다른 포맷). 원본은 5.기타/_백업/에 보존(#16).
- 추가: 클로즈감사 JSON에서 Workflow2 대상(문제카드 보유 파일) 목록 산출.
"""
import os, re, json, glob, shutil

CARD_DIR = r"H:\내 드라이브\outputs\02_cards_v37"
BACKUP   = r"H:\내 드라이브\5.기타\_백업\카드마커정규화_2026-06-22"
AUDIT_JSON = r"H:\내 드라이브\.agent\state\_cloze_audit_2026-06-21.json"
TARGETS  = r"H:\내 드라이브\.agent\state\_cloze_review_targets.json"

FULLWIDTH = re.compile(r"【[\s　]*(.+?)[\s　]*】")

os.makedirs(BACKUP, exist_ok=True)

print("===== 1) 전각괄호 【】 → {{}} 정규화 =====")
converted = []
for fp in glob.glob(os.path.join(CARD_DIR, "*.md")):
    fn = os.path.basename(fp)
    if fn.startswith("찌라시"):
        continue
    with open(fp, encoding="utf-8") as f:
        txt = f.read()
    if "【" not in txt:
        continue
    n = len(FULLWIDTH.findall(txt))
    if n == 0:
        continue
    shutil.copy2(fp, os.path.join(BACKUP, fn))           # 원본 백업
    new = FULLWIDTH.sub(lambda m: "{{" + m.group(1).strip() + "}}", txt)
    leftover = new.count("【") + new.count("】")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(new)
    converted.append((fn, n, leftover))
    print(f"  {fn}: {n}건 변환, 잔여 괄호 {leftover}")
print(f"  → {len(converted)}파일, 총 {sum(c[1] for c in converted)}건 변환. 백업: {BACKUP}")

print("\n===== 2) Workflow2 대상 파일 목록 =====")
with open(AUDIT_JSON, encoding="utf-8") as f:
    audit = json.load(f)
files = [v for v in audit["by_file"].values() if v["n_flagged"] > 0]
files.sort(key=lambda x: -x["n_flagged"])
# 찌라시/법조윤리(비표준 카드) 제외 옵션 표시만
targets = [{"file": v["file"], "n_cards": v["n_cards"], "n_flagged": v["n_flagged"],
           "issue_types": v["issue_types"]} for v in files]
with open(TARGETS, "w", encoding="utf-8") as f:
    json.dump(targets, f, ensure_ascii=False, indent=2)
print(f"  문제카드 보유 파일: {len(targets)} / 전체 {len(audit['by_file'])}")
print(f"  상위 5: " + ", ".join(f"{t['file'][:30]}({t['n_flagged']})" for t in targets[:5]))
print(f"  [written] {TARGETS}")
