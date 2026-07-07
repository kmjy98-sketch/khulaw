# -*- coding: utf-8 -*-
"""OCR 현황 스캔(읽기전용) — outputs/01_ocr_llamaparse/ 책별 커버리지·헤더·잘림 진단.
PDF 미사용(OCR 마크다운만 분석). 2026-06-26."""
import glob, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
OUT = r"E:\법학볼트\outputs\01_ocr_llamaparse"

books = {}
for f in glob.glob(os.path.join(OUT, "*_llamaparse_p*.md")):
    base = os.path.basename(f)
    m = re.match(r"(.+)_llamaparse_p(\d+)-(\d+)\.md$", base)
    if not m:
        continue
    pre, a, b = m.group(1), int(m.group(2)), int(m.group(3))
    try:
        txt = open(f, encoding="utf-8").read()
    except Exception:
        txt = ""
    d = books.setdefault(pre, {"chunks": [], "chars": 0, "headers": 0})
    d["chunks"].append((a, b))
    d["chars"] += len(txt)
    d["headers"] += len(re.findall(r"(?m)^#{1,6}\s", txt))

print("%-26s %5s %5s %6s %8s %5s  %s" % ("book", "chunk", "maxP", "gaps", "chars", "hdr", "비고"))
print("-" * 90)
for pre in sorted(books):
    d = books[pre]
    ch = sorted(d["chunks"])
    maxp = max(b for _, b in ch)
    minp = min(a for a, _ in ch)
    # gap 탐지(청크 사이 끊김)
    gaps = 0
    cur = minp
    for a, b in ch:
        if a > cur + 1:
            gaps += 1
        cur = max(cur, b)
    note = ""
    if minp > 1:
        note += "시작%d " % minp
    if gaps:
        note += "내부gap%d " % gaps
    print("%-26s %5d %5d %6d %8d %5d  %s" % (pre, len(ch), maxp, gaps, d["chars"], d["headers"], note))

print("\n총 %d책 / 총청크 %d" % (len(books), sum(len(v["chunks"]) for v in books.values())))
