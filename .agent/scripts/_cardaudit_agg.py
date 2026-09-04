# -*- coding: utf-8 -*-
"""카드감사 집계 — 논점노트 frontmatter '카드감사:' 마커에서 누락건수 추출, 과목별 집계.
세션한도와 무관(로컬 파일 처리). 결과 → .agent/state/cardaudit_집계.md + stdout."""
import glob, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"E:\법학볼트"; WIKI = os.path.join(ROOT, "sync", "위키"); STATE = os.path.join(ROOT, ".agent", "state")
SUBJ = ["민법", "형법총론", "형법각론", "헌법", "민사소송법", "민사집행법"]
rows = []; L = ["# 카드감사 집계 (전수 마커 기반)", ""]
L.append("| 과목 | 감사완료 | 전체 | 총누락(건) | 평균 | 카드없음 논점 | 누락>=8 논점 |")
L.append("|---|---:|---:|---:|---:|---:|---:|")
gT=gD=gO=0
detail = []
for s in SUBJ:
    files = [f for f in glob.glob(os.path.join(WIKI, s, "*.md")) if not os.path.basename(f).startswith("_")]
    tot = len(files); done = 0; omit = 0; nocard = 0; high = []
    for f in files:
        try: txt = open(f, encoding="utf-8").read()
        except Exception: continue
        m = re.search(r"(?m)^카드감사:\s*(.+)$", txt)
        if not m: continue
        line = m.group(1); done += 1
        nm = re.search(r"누락\s*(\d+)\s*건", line)
        n = int(nm.group(1)) if nm else 0
        omit += n
        if "카드없음" in line: nocard += 1
        if n >= 8: high.append((os.path.basename(f)[:-3], n))
    avg = round(omit/done, 1) if done else 0
    high.sort(key=lambda x:-x[1])
    L.append(f"| {s} | {done} | {tot} | {omit} | {avg} | {nocard} | {len(high)} |")
    gT += tot; gD += done; gO += omit
    if high:
        detail.append(f"\n### {s} 누락>=8 논점 (총 {len(high)})")
        detail += [f"- {t} — {n}건" for t,n in high[:25]]
L.append(f"| **합계** | **{gD}** | **{gT}** | **{gO}** | **{round(gO/gD,1) if gD else 0}** | | |")
L.append("")
L += detail
out = os.path.join(STATE, "cardaudit_집계.md")
open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L[:14]))
print(f"\n[작성] {out}  (감사 {gD}/{gT}, 총누락 {gO}건)")
