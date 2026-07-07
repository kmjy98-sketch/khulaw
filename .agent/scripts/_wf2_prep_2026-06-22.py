#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Workflow2 준비: 클로즈감사 JSON → 고신뢰 결함 파일 필터 → 사전 백업 → WF2 args 생성.
감사 재실행은 별도(_cloze_audit_2026-06-21.py)로 먼저 돌린 뒤 이 스크립트 실행.
"""
import os, json, shutil, glob

CARD_DIR = r"H:\내 드라이브\outputs\02_cards_v37"
AUDIT = r"H:\내 드라이브\.agent\state\_cloze_audit_2026-06-21.json"
BACKUP = r"H:\내 드라이브\5.기타\_백업\카드클로즈수정_2026-06-22"
ARGS = r"H:\내 드라이브\.agent\state\_wf2_args.json"

# 잔여 실작업만 (파편=house style 다수라 제외, 누설·cloze過다=오탐/판단 제외)
HIGH = {"anchor_cloze", "빈칸라벨_있으나_cloze0"}

os.makedirs(BACKUP, exist_ok=True)
with open(AUDIT, encoding="utf-8") as f:
    audit = json.load(f)

items = []
for v in audit["by_file"].values():
    it = v.get("issue_types", {})
    hit = HIGH & set(it.keys())
    if not hit:
        continue
    fn = v["file"]
    if fn.startswith("찌라시"):   # 찌라시는 비표준 포맷 — 제외
        continue
    score = sum(it.get(k, 0) for k in HIGH)
    flagstr = ", ".join(f"{k}{it[k]}" for k in it)
    items.append({"file": fn, "path": (CARD_DIR + "\\" + fn).replace("\\", "/"),
                  "flags": flagstr, "score": score})

items.sort(key=lambda x: -x["score"])

# 사전 백업
backed = 0
for it in items:
    src = os.path.join(CARD_DIR, it["file"])
    dest = os.path.join(BACKUP, it["file"])
    if os.path.exists(src) and not os.path.exists(dest):   # 기존 원본 백업 보존(덮어쓰기 금지)
        shutil.copy2(src, dest)
        backed += 1

out = {"items": [{"file": i["file"], "path": i["path"], "flags": i["flags"]} for i in items],
       "verify_sample": max(8, len(items) // 12)}
with open(ARGS, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"WF2 대상 파일: {len(items)} (백업 {backed} → {BACKUP})")
print(f"verify_sample: {out['verify_sample']}")
print("상위10:")
for i in items[:10]:
    print(f"  {i['score']:4d}  {i['file']}  [{i['flags']}]")
print(f"[written] {ARGS}")
