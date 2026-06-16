"""민사소송법사례연습 독해분할 → 작업용/민소사례/, 원본 → 작업용/_원본/.
정찰 w9xizcd9y 의 split_plan 적용. 마지막 세그 end는 total로 자동 확장.
"""
import sys, os, shutil
from pathlib import Path
from pypdf import PdfReader, PdfWriter

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"H:\내 드라이브")
SRC = ROOT / "1.민사/94.교재/민사소송법사례연습_8판_26.pdf"
OUTDIR = ROOT / "작업용/민소사례"
ORIG = ROOT / "작업용/_원본"
BOOK, YEAR = "민소사례", "26"
SEGS = [("목차", 1, 12), ("소송주체", 13, 60), ("소송개시", 61, 87), ("변론", 88, 135),
        ("증거", 136, 162), ("소송종료", 163, 272), ("병합소송", 273, 414), ("상소재심", 415, 451)]

reader = PdfReader(str(SRC))
total = len(reader.pages)
# 마지막 세그 end를 total로 클램프
SEGS[-1] = (SEGS[-1][0], SEGS[-1][1], total)
covered = []
for _, s, e in SEGS:
    covered.extend(range(s, e + 1))
miss = sorted(set(range(1, total + 1)) - set(covered))
dup = len(covered) - len(set(covered))
print(f"[원본] {SRC.name} 총{total}p  miss={miss[:10]} dup={dup}")
if miss or dup:
    print("⚠ 커버리지 문제 — 중단"); sys.exit(1)
OUTDIR.mkdir(parents=True, exist_ok=True)
for label, s, e in SEGS:
    w = PdfWriter()
    for p in range(s - 1, e):
        w.add_page(reader.pages[p])
    out = OUTDIR / f"{BOOK}_{label}_{YEAR}.pdf"
    with open(out, "wb") as f:
        w.write(f)
    mb = out.stat().st_size / 1048576
    flag = "  ⚠>80MB" if mb > 80 else ""
    print(f"  [생성] {out.name}  p.{s}-{e} ({e - s + 1}p, {mb:.1f}MB){flag}")
# 원본 → 작업용/_원본/
ORIG.mkdir(parents=True, exist_ok=True)
dst = ORIG / f"{BOOK}_원본_{YEAR}.pdf"
if not dst.exists():
    shutil.move(str(SRC), str(dst))
    print(f"  [_원본 이동] {SRC.name} → {dst.name}")
print("완료")
