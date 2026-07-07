#!/usr/bin/env python
"""과목별 목차 회복 OCR — 2026-06-26. 각 정본 교재의 목차 PDF를 LlamaParse OCR(작음·빠름).
목차=닫힌루프 고정점. ocr_extract_v3.py 위임. skip-existing 재개."""
import os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import vp  # noqa: E402
PY = sys.executable
SCRIPT = vp(".agent", "scripts", "ocr_extract_v3.py")
OUT = vp("outputs", "01_ocr_llamaparse")
TIER = "agentic"
# (목차 PDF 절대상대경로, prefix, 책명, 과목)
TOCS = [
    ("2.형사/반반형법/반반형법_목차_26.pdf", "반반형법_목차", "반반형법 목차", "형사"),
    ("3.공법/헌법300/헌법300_목차_26.pdf", "헌법300_목차", "헌법핵심정리300 목차", "공법"),
    ("3.공법/_원본보관/행정법강해/행정법강해_00_목차.pdf", "행정법강해_목차", "행정법강해 목차", "공법"),
    ("1.민사/_원본보관/논점민집/논점민집_00_목차.pdf", "논점민집_목차", "논점 민사집행법 목차", "민사"),
    ("1.민사/_강의/34.송영곤_민소/교재/논점민소/논점민소_목차_26.pdf", "논점민소_목차", "논점 민사소송법 목차", "민사"),
]
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"목차 OCR 시작 {len(TOCS)}권 (tier={TIER})", flush=True)
    for i, (rel, prefix, book, subj) in enumerate(TOCS, 1):
        p = vp(*rel.split("/"))
        if not os.path.exists(p):
            print(f"[{i}/{len(TOCS)}] MISSING {rel}", flush=True); continue
        print(f"[{i}/{len(TOCS)}] {book}", flush=True)
        t0 = time.time()
        try:
            r = subprocess.run([PY, SCRIPT, "--engine", "llamaparse", "--pdf", p, "--out", OUT,
                                "--prefix", prefix, "--book", book, "--subject", subj, "--tier", TIER])
            print(f"[{i}/{len(TOCS)}] rc={r.returncode} {round((time.time()-t0)/60,1)}min", flush=True)
        except Exception as e:
            print(f"[{i}/{len(TOCS)}] ERROR {e}", flush=True)
    print("목차 OCR 완료", flush=True)
if __name__ == "__main__":
    main()
