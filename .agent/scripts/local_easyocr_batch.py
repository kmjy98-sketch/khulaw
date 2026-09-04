#!/usr/bin/env python
"""로컬 easyocr 배치 러너 — 스캔본 우선순위 연속 OCR (CPU), 2026-06-01

- Colab marker-pdf 불가 → 로컬 easyocr 단독 경로.
- 우선순위 순서로 책을 하나씩 local_easyocr_extract.py 서브프로세스 호출.
- 각 책은 30p 청크로 outputs/01_ocr/에 저장, 이미 있으면 skip(재개 가능).
- 한 책 실패해도 다음 책 계속. 중간 종료/재시작해도 이어서 진행.
- 진행 로그는 stdout(배치 출력 파일)로 흐름.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

PY = sys.executable
SCRIPT = vp(".agent", "scripts", "local_easyocr_extract.py")
WORK = Path(vp("작업용"))
OUT = vp("outputs", "01_ocr")

# (pdf 파일명, prefix, 책명, 저자, 과목)  — 우선순위 순(작고 핵심부터)
BOOKS = [
    ("송영곤_신민사법선택형연습1_민법총칙_26.pdf", "신민사법선택형_민총_easyocr", "신민사법 선택형연습 1 민법총칙", "송영곤", "민사"),
    ("송영곤_신민사법선택형연습1_물권법_26.pdf", "신민사법선택형_물권_easyocr", "신민사법 선택형연습 1 물권법", "송영곤", "민사"),
    ("송영곤_신민사법선택형연습1_채권법1_26.pdf", "신민사법선택형_채권1_easyocr", "신민사법 선택형연습 1 채권법1", "송영곤", "민사"),
    ("송영곤_신민사법선택형연습1_채권법2_26.pdf", "신민사법선택형_채권2_easyocr", "신민사법 선택형연습 1 채권법2", "송영곤", "민사"),
    ("2026 표준판례 반영 헌법 핵심정리 300 - 각종 국가고시 대비, 제3전정4판,_3c_r6_d2.pdf", "헌법핵심정리300_easyocr", "헌법 핵심정리 300", "금동흠", "공법"),
    ("김기용_형법총론_교안_26.pdf", "김기용_형총교안_easyocr", "형법총론 교안 2026", "김기용", "형사"),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"배치 시작: {len(BOOKS)}권 (우선순위 순)", flush=True)
    print("=" * 60, flush=True)
    t_all = time.time()
    for idx, (pdf, prefix, book, author, subj) in enumerate(BOOKS, 1):
        p = WORK / pdf
        if not p.exists():
            print(f"[{idx}/{len(BOOKS)}] [MISSING] {pdf}", flush=True)
            continue
        print(f"\n[{idx}/{len(BOOKS)}] ===== {book} =====", flush=True)
        t0 = time.time()
        try:
            r = subprocess.run(
                [PY, SCRIPT, "--pdf", str(p), "--out", OUT,
                 "--prefix", prefix, "--book", book, "--author", author, "--subject", subj],
            )
            print(f"[{idx}/{len(BOOKS)}] {book} rc={r.returncode} {round((time.time()-t0)/60,1)}min", flush=True)
        except Exception as e:
            print(f"[{idx}/{len(BOOKS)}] {book} ERROR: {e}", flush=True)
    print("\n" + "=" * 60, flush=True)
    print(f"배치 완료. 총 {round((time.time()-t_all)/3600,1)}h", flush=True)


if __name__ == "__main__":
    main()
