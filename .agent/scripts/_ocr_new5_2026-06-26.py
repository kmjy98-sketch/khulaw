#!/usr/bin/env python
"""신규 5권(_원본보관 '새로 산 책') LlamaParse OCR — 2026-06-26 (일회성).
10.도서관 PDF → outputs/01_ocr_llamaparse/. 청크(30p) skip-existing 재개. ocr_extract_v3.py 위임.
대상: 논점민집·신민사법선택형_민소(민사) / compact형각OX·형법요론각론(형사) / 행정법강해(공법).
LLAMA_CLOUD_API_KEY(.env) 필요. 책별 독립 — 한 권 실패해도 다음 권 계속."""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import vp  # noqa: E402

PY = sys.executable
SCRIPT = vp(".agent", "scripts", "ocr_extract_v3.py")
OUT = vp("outputs", "01_ocr_llamaparse")
LIB = vp("10.도서관")
TIER = "agentic"

# (pdf 파일명(10.도서관), prefix, 책명, 저자, 과목)
BOOKS = [
    ("논점민집.pdf", "논점민사집행법_llamaparse", "논점 민사집행법", "", "민사"),
    ("신민사법선택형_민소.pdf", "신민사법선택형_민소_llamaparse", "신민사법 선택형연습 민사소송법", "송영곤", "민사"),
    ("compact형각OX.pdf", "compact형각OX_llamaparse", "compact 형법각론 OX", "", "형사"),
    ("형법요론_각론.pdf", "형법요론각론_llamaparse", "형법요론 각론", "", "형사"),
    ("행정법강해.pdf", "행정법강해_llamaparse", "행정법강해", "", "공법"),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"신규 5권 LlamaParse OCR 시작 (tier={TIER}, out={OUT})", flush=True)
    print("=" * 60, flush=True)
    t_all = time.time()
    for i, (pdf, prefix, book, author, subj) in enumerate(BOOKS, 1):
        p = os.path.join(LIB, pdf)
        if not os.path.exists(p):
            print(f"[{i}/5] [MISSING] {p}", flush=True)
            continue
        print(f"\n[{i}/5] ===== {book} =====", flush=True)
        t0 = time.time()
        try:
            r = subprocess.run(
                [PY, SCRIPT, "--engine", "llamaparse", "--pdf", p, "--out", OUT,
                 "--prefix", prefix, "--book", book, "--author", author,
                 "--subject", subj, "--tier", TIER])
            print(f"[{i}/5] {book} rc={r.returncode} {round((time.time()-t0)/60,1)}min", flush=True)
        except Exception as e:
            print(f"[{i}/5] {book} ERROR: {e}", flush=True)
    print("\n" + "=" * 60, flush=True)
    print(f"배치 완료. 총 {round((time.time()-t_all)/3600,2)}h", flush=True)


if __name__ == "__main__":
    main()
