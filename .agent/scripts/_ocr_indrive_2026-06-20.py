#!/usr/bin/env python
"""LlamaParse 배치 — "있는 책부터" (드라이브 보유 스캔본 4종), 2026-06-20

사용자 지시: "일단 있는 책부터 진행". 스캔 대기 중인 책(행정법강해·신민사선택형2·
형법각론OX·논점민사집행법 풀북)은 제외하고, 이미 드라이브에 있는 4종만 OCR.

- local_llamaparse_batch.py 와 동일 구조(ocr_extract_v3.py subprocess 호출).
- 단, 소스가 작업용/ 밖이라 PDF 절대경로 사용. 청크(30p) skip-existing → 재개 가능.
- 출력 outputs/01_ocr_llamaparse/ (기존 산출물 보존 #16).

분량/크레딧(2026-06-20 산정):
  민소사례 ~436p + 쟁점노트 소송집행 ~341p + 쟁점노트 가족법 ~62p + 기초법리집행법 ~26p
  = 약 865p.  cost_effective(3cr/p)=2,595cr / agentic(10cr/p)=8,650cr.
  무료 티어 10,000cr/월 안에 들어감(agentic도 한 달이면 가능). 실행 전 크레딧 잔량 확인 권장.

실행:
  python .agent/scripts/_ocr_indrive_2026-06-20.py                # 기본 tier=agentic(기존 코퍼스와 동일 품질)
  python .agent/scripts/_ocr_indrive_2026-06-20.py --tier cost_effective   # 크레딧 절약
  python .agent/scripts/_ocr_indrive_2026-06-20.py --only 민소사례          # 한 권만

후속: korean-law-mcp 사건·조문 전수검증(#34) → 02-wiki → 02-card.
"""
import subprocess
import sys
import time
import argparse
from pathlib import Path

PY = sys.executable
SCRIPT = r"H:\내 드라이브\.agent\scripts\ocr_extract_v3.py"
OUT = r"H:\내 드라이브\outputs\01_ocr_llamaparse"
ROOT = Path(r"H:\내 드라이브")

# (PDF 절대경로(ROOT 상대), prefix, 책명, 저자, 과목)
BOOKS = [
    (r"10.도서관\민소사례_원본_26.pdf",
     "민소사례_llamaparse", "송영곤 민사소송법 사례연습 2026", "송영곤", "민사소송법"),
    (r"10.도서관\민사법쟁점노트_소송집행_26.pdf",
     "쟁점노트_소송집행_llamaparse", "민사법 쟁점노트 소송·집행 2026", "송영곤", "민사소송법"),
    (r"1.민사\_강의\33.송영곤_쟁노\교재\민사법쟁점노트\민사법쟁점노트_가족법_26.pdf",
     "쟁점노트_가족법_llamaparse", "민사법 쟁점노트 가족법 2026", "송영곤", "민사"),
    (r"1.민사\_강의\송영곤_기본민법\강의자료\논점민법강의_기초법리_민사집행법_26.pdf",
     "기초법리집행법_llamaparse", "논점민법강의 기초법리 민사집행법 2026", "송영곤", "민사집행법"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default="agentic",
                    help="agentic(기본, 코퍼스 동일) | cost_effective(크레딧 1/3)")
    ap.add_argument("--only", default=None, help="prefix 일부 문자열로 한 권만 선택")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    sel = [b for b in BOOKS if (args.only is None or args.only in b[1] or args.only in b[2])]
    print(f"LlamaParse 배치(있는 책부터): {len(sel)}/{len(BOOKS)}권, tier={args.tier}", flush=True)
    print("=" * 60, flush=True)
    t_all = time.time()
    for idx, (rel, prefix, book, author, subj) in enumerate(sel, 1):
        p = ROOT / rel
        if not p.exists():
            print(f"[{idx}/{len(sel)}] [MISSING] {p}", flush=True)
            continue
        print(f"\n[{idx}/{len(sel)}] ===== {book} =====\n  src: {p}", flush=True)
        t0 = time.time()
        try:
            r = subprocess.run(
                [PY, SCRIPT, "--engine", "llamaparse", "--pdf", str(p), "--out", OUT,
                 "--prefix", prefix, "--book", book, "--author", author,
                 "--subject", subj, "--tier", args.tier],
            )
            print(f"[{idx}/{len(sel)}] {book} rc={r.returncode} "
                  f"{round((time.time()-t0)/60,1)}min", flush=True)
        except Exception as e:
            print(f"[{idx}/{len(sel)}] {book} ERROR: {e}", flush=True)
    print("\n" + "=" * 60, flush=True)
    print(f"배치 완료. 총 {round((time.time()-t_all)/3600,1)}h", flush=True)


if __name__ == "__main__":
    main()
