# -*- coding: utf-8 -*-
"""위키 재구축 진행·검증 현황 — frontmatter '상태' 마커 기반(완료/중단 구분). 2026-06-26.
- 검증완료: 원문보존 + OCR대비 검증 끝(=완료). 그 외(검토대기/원문보존)=미검증(중단가능). 검증실패=재생성 대상.
- 누락=MOC 논점 중 노트 없음. 의심=700B 미만(요약/빈). 백링크없음=[[ ]] 0.
재실행: python .agent/scripts/_rebuild_status.py  →  .agent/state/rebuild_진행현황.md"""
import glob, os, re, sys
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"E:\법학볼트"; WIKI = os.path.join(ROOT, "sync", "위키")
OUT = os.path.join(ROOT, ".agent", "state", "rebuild_진행현황.md")
TINY = 700

NOISE = {"쟁점", "제목", "MOC", "_MOC"}
def targets(sd):
    t = set()
    for m in glob.glob(os.path.join(sd, "_*목차*.md")):
        try: lines = open(m, encoding="utf-8").read().splitlines()
        except Exception: lines = []
        for ln in lines:
            if ln.lstrip().startswith(">"):  # 범례·설명줄 제외(오탐 방지)
                continue
            for x in re.findall(r"\[\[([^\]]+)\]\]", ln):
                x = x.strip()
                if x and not x.startswith("_") and x not in NOISE:
                    t.add(x)
    return t

def status_of(c):
    m = re.search(r"(?m)^상태:\s*(.+)$", c)
    s = (m.group(1).strip() if m else "")
    if "검증완료" in s: return "완료"
    if "검증실패" in s: return "실패"
    return "미검증"

rows = []
subs = sorted([d for d in os.listdir(WIKI) if os.path.isdir(os.path.join(WIKI, d)) and d != "쟁점"])
for s in subs:
    sd = os.path.join(WIKI, s)
    tgt = targets(sd)
    notes = [f for f in glob.glob(os.path.join(sd, "*.md")) if not os.path.basename(f).startswith("_")]
    names = {os.path.splitext(os.path.basename(f))[0] for f in notes}
    done = wait = fail = tiny = nolink = 0
    for f in notes:
        try: c = open(f, encoding="utf-8").read()
        except Exception: c = ""
        st = status_of(c)
        done += st == "완료"; wait += st == "미검증"; fail += st == "실패"
        if len(c.encode("utf-8")) < TINY: tiny += 1
        if "[[" not in c: nolink += 1
    miss = sorted(tgt - names) if tgt else []
    rows.append((s, len(tgt), done, wait, fail, len(miss), tiny, nolink, miss[:6]))

L = [f"# 위키 재구축 진행·검증 현황 (갱신 {datetime.now():%Y-%m-%d %H:%M})",
     "> 파일시스템·frontmatter 실측. 완료=검증완료 마커. 중단돼도 재실행하면 현재 상태.\n",
     "| 과목 | 목표 | 완료✅ | 미검증 | 실패 | 누락 | 의심(작은) | 링크없음 |",
     "|---|---:|---:|---:|---:|---:|---:|---:|"]
T = [0]*6
for s, t, d, w, fa, mi, ti, nl, _ in rows:
    L.append(f"| {s} | {t} | {d} | {w} | {fa} | {mi} | {ti} | {nl} |")
    for i, v in enumerate([t, d, w, fa, mi, 0]): T[i] += v
L.append(f"| **합계** | **{T[0]}** | **{T[1]}** | **{T[2]}** | **{T[3]}** | **{T[4]}** | | |")
L.append("")
for s, t, d, w, fa, mi, ti, nl, ex in rows:
    if ex: L.append(f"- {s} 누락: {', '.join(ex)}")
rep = "\n".join(L) + "\n"
open(OUT, "w", encoding="utf-8").write(rep)
print(rep); print(f"[기록] {OUT}")
