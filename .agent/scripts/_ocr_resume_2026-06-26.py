#!/usr/bin/env python
"""OCR 이어서 진행 — 2026-06-26. 미실행/잘림분 보충. 청크 skip-existing 재개(중단안전).
- 행정법강해: 미실행(전권)
- 쟁점노트_재산법: 잘림(616p책 OCR 390p) → skip-existing으로 p391-616(물권) 보충
ocr_extract_v3.py 위임. LLAMA_CLOUD_API_KEY(.env). 책별 독립."""
import os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import vp  # noqa: E402

PY = sys.executable
SCRIPT = vp(".agent", "scripts", "ocr_extract_v3.py")
OUT = vp("outputs", "01_ocr_llamaparse")
LIB = vp("10.도서관")
TIER = "agentic"
BOOKS = [
    ("행정법강해.pdf", "행정법강해_llamaparse", "행정법강해", "", "공법"),
    ("민사법쟁점노트_재산법_26.pdf", "쟁점노트_재산법_llamaparse", "민사법 쟁점노트 재산법", "", "민사"),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"OCR 보충 시작 (tier={TIER})", flush=True)
    t_all = time.time()
    for i, (pdf, prefix, book, author, subj) in enumerate(BOOKS, 1):
        p = os.path.join(LIB, pdf)
        if not os.path.exists(p):
            print(f"[{i}/{len(BOOKS)}] [MISSING] {p}", flush=True)
            continue
        print(f"\n[{i}/{len(BOOKS)}] ===== {book} =====", flush=True)
        t0 = time.time()
        try:
            r = subprocess.run([PY, SCRIPT, "--engine", "llamaparse", "--pdf", p, "--out", OUT,
                                "--prefix", prefix, "--book", book, "--author", author,
                                "--subject", subj, "--tier", TIER])
            print(f"[{i}/{len(BOOKS)}] {book} rc={r.returncode} {round((time.time()-t0)/60,1)}min", flush=True)
        except Exception as e:
            print(f"[{i}/{len(BOOKS)}] {book} ERROR: {e}", flush=True)
    print(f"\n보충 완료. 총 {round((time.time()-t_all)/3600,2)}h", flush=True)


if __name__ == "__main__":
    main()
