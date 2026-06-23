#!/usr/bin/env python
"""LlamaParse 배치 러너 — 전권 LlamaParse 재추출 (클라우드), 2026-06-03

- ocr_extract_v3.py --engine llamaparse 를 책별 subprocess 호출.
- 출력 outputs/01_ocr_llamaparse/ (기존 01_ocr/ easyocr 산출물 보존 #16).
- 청크(30p)별 skip-existing → 중단/재시작 재개. 한 책 실패해도 다음 책 계속.
- tier=agentic. LLAMA_CLOUD_API_KEY(.env) 필요.

산출: outputs/01_ocr_llamaparse/{prefix}_p{NNN}-{NNN}.md  (+ {prefix}_ocrlog.json)
후속: korean-law-mcp 사건번호 전수검증(#34) → 02-wiki → 02-card.
"""
import os
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

PY = sys.executable
SCRIPT = vp(".agent", "scripts", "ocr_extract_v3.py")
WORK = Path(vp("작업용"))
OUT = vp("outputs", "01_ocr_llamaparse")
TIER = "agentic"

# (pdf 파일명, prefix, 책명, 저자, 과목) — 우선순위 순(현재 작업/작은 책부터)
BOOKS = [
    ("논점민법강의_재산법_26.pdf", "논점민법재산법_llamaparse", "논점민법강의 재산법 2026", "송영곤", "민사"),
    ("송영곤_신민사법선택형연습1_민법총칙_26.pdf", "신민사법선택형_민총_llamaparse", "신민사법 선택형연습 1 민법총칙", "송영곤", "민사"),
    ("송영곤_신민사법선택형연습1_물권법_26.pdf", "신민사법선택형_물권_llamaparse", "신민사법 선택형연습 1 물권법", "송영곤", "민사"),
    ("송영곤_신민사법선택형연습1_채권법1_26.pdf", "신민사법선택형_채권1_llamaparse", "신민사법 선택형연습 1 채권법1", "송영곤", "민사"),
    ("송영곤_신민사법선택형연습1_채권법2_26.pdf", "신민사법선택형_채권2_llamaparse", "신민사법 선택형연습 1 채권법2", "송영곤", "민사"),
    ("2026 표준판례 반영 헌법 핵심정리 300 - 각종 국가고시 대비, 제3전정4판,_3c_r6_d2.pdf", "헌법핵심정리300_llamaparse", "헌법 핵심정리 300", "금동흠", "공법"),
    ("김기용_형법총론_교안_26.pdf", "김기용_형총교안_llamaparse", "형법총론 교안 2026", "김기용", "형사"),
    # ── 추가 18권 (2026-06-03 결정, idx 7~24). 병렬 실행: --from-idx 7 ──
    ("송영곤_신민사법선택형연습1_인적담보_26.pdf", "신민사법선택형_인적담보_llamaparse", "신민사법 선택형연습 1 인적담보", "송영곤", "민사"),
    ("송영곤_신민사법선택형연습1_물적담보_26.pdf", "신민사법선택형_물적담보_llamaparse", "신민사법 선택형연습 1 물적담보", "송영곤", "민사"),
    ("송영곤_신민사법선택형연습1_가족법_26.pdf", "신민사법선택형_가족법_llamaparse", "신민사법 선택형연습 1 가족법", "송영곤", "민사"),
    ("민사법쟁점노트_재산법_26.pdf", "쟁점노트_재산법_llamaparse", "민사법 쟁점노트 재산법", "", "민사"),
    ("민사법쟁점노트_소송,집행_26.pdf", "쟁점노트_소송집행_llamaparse", "민사법 쟁점노트 소송·집행", "", "민사"),
    ("민사법쟁점노트_가족법_26.pdf", "쟁점노트_가족법_llamaparse", "민사법 쟁점노트 가족법", "", "민사"),
    ("송영곤_사례연습_채권_26.pdf", "사례연습_채권_llamaparse", "송영곤 사례연습 채권", "송영곤", "민사"),
    ("송영곤_사례연습_물권_26.pdf", "사례연습_물권_llamaparse", "송영곤 사례연습 물권", "송영곤", "민사"),
    ("송영곤_사례연습_민총_26.pdf", "사례연습_민총_llamaparse", "송영곤 사례연습 민총", "송영곤", "민사"),
    ("송영곤_사례연습_담보_26.pdf", "사례연습_담보_llamaparse", "송영곤 사례연습 담보", "송영곤", "민사"),
    ("송영곤_사례연습_가족_26.pdf", "사례연습_가족_llamaparse", "송영곤 사례연습 가족", "송영곤", "민사"),
    ("COMPACT 형법 - 반반형법 플러스, 제4판_3c_r6_d2.pdf", "반반형법플러스_llamaparse", "COMPACT 형법 반반형법 플러스 제4판", "", "형사"),
    ("compact형법총론OX_26.pdf", "compact형총OX_llamaparse", "compact 형법총론 OX", "", "형사"),
    ("작은변사기형법_25.pdf", "작은변사기형법_llamaparse", "작은변사기형법", "", "형사"),
    ("유니온 헌법 기출편(2027 대비).pdf", "유니온헌법기출_llamaparse", "유니온 헌법 기출편 2027", "", "공법"),
    ("[5+1] 2027 해커스변호사 변호사시험 기출문제집 헌법 사례형 - 최신개정판ㅣ변호사시험 등 각종 국가고_3c_r6_d2.pdf", "해커스헌법사례형_llamaparse", "해커스 변호사 기출문제집 헌법 사례형 2027", "", "공법"),
    ("2026 논점 민사소송법 - 변호사 시험 & 각종 국가고시 대비,_3c_r6_d2.pdf", "논점민사소송법_llamaparse", "2026 논점 민사소송법", "", "민사"),
    ("2026 민사법 사례연습 1 - 진도별 요약형 - 제2판_3c_r6_d2 (1).pdf", "민사법사례연습1_llamaparse", "2026 민사법 사례연습 1 진도별 요약형 제2판", "", "민사"),
]


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-idx", type=int, default=0, help="BOOKS 시작 인덱스(0-based, 포함)")
    ap.add_argument("--to-idx", type=int, default=len(BOOKS), help="끝 인덱스(exclusive)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sel = BOOKS[args.from_idx:args.to_idx]
    print(f"LlamaParse 배치 시작: {len(sel)}/{len(BOOKS)}권 "
          f"(idx {args.from_idx}~{args.to_idx}, tier={TIER})", flush=True)
    print("=" * 60, flush=True)
    t_all = time.time()
    for idx, (pdf, prefix, book, author, subj) in enumerate(sel, args.from_idx + 1):
        p = WORK / pdf
        if not p.exists():
            print(f"[{idx}/{len(BOOKS)}] [MISSING] {pdf}", flush=True)
            continue
        print(f"\n[{idx}/{len(BOOKS)}] ===== {book} =====", flush=True)
        t0 = time.time()
        try:
            r = subprocess.run(
                [PY, SCRIPT, "--engine", "llamaparse", "--pdf", str(p), "--out", OUT,
                 "--prefix", prefix, "--book", book, "--author", author,
                 "--subject", subj, "--tier", TIER],
            )
            print(f"[{idx}/{len(BOOKS)}] {book} rc={r.returncode} "
                  f"{round((time.time()-t0)/60,1)}min", flush=True)
        except Exception as e:
            print(f"[{idx}/{len(BOOKS)}] {book} ERROR: {e}", flush=True)
    print("\n" + "=" * 60, flush=True)
    print(f"배치 완료. 총 {round((time.time()-t_all)/3600,1)}h", flush=True)


if __name__ == "__main__":
    main()
