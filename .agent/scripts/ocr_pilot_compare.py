#!/usr/bin/env python
"""OCR 파일럿 비교 하니스 — 동일 PDF/페이지를 여러 엔진으로 추출·비교, 2026-06-03

목적: easyocr(기준선) vs llamaparse(추후 upstage/gemini)를 같은 입력에 돌려
      ㉠추출 글자수 ㉡사건번호 후보수 ㉢조문수 ㉣소요시간 1차 비교.
      ※ 정확도 채점은 korean-law-mcp 로 별도 단계(여기선 추출량·anchor 밀도 신호만).

사용:
  python ocr_pilot_compare.py --pdf "작업용/논점민법강의_재산법_26.pdf" --pages 61-63 \
    --engines easyocr,llamaparse --book "논점민법강의 재산법 2026" --author 송영곤 --subject 민사 [--tier agentic]

  # 키 없으면 우선 기준선만:  --engines easyocr

출력:
  .agent/data/ocr_pilot/{stem}_{engine}_p{S}-{E}.md   (엔진별 추출본)
  .agent/data/ocr_pilot/_compare_{stem}_p{S}-{E}.md   (비교표)
"""
import os
import sys
import re
import time
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fitz
from ocr_extract_v3 import ENGINES, write_chunk

PILOT_DIR = r"H:\내 드라이브\.agent\data\ocr_pilot"

# 사건번호 근사: 연도(2~4자리)+한글(1~3)+일련번호. 예) 76다1437, 2002다5873, 4292민상252, 64민상9
CASE_RE = re.compile(r"\d{2,4}\s?[가-힣]{1,3}\s?\d{1,6}")
JO_RE = re.compile(r"제\s*\d+\s*조")


def metrics(pages):
    text = "\n".join(t for _, t in pages)
    return {
        "chars": len(re.sub(r"\s", "", text)),
        "cases": len(CASE_RE.findall(text)),
        "jo": len(JO_RE.findall(text)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True, help="예: 61-63 (PDF 물리 페이지 기준)")
    ap.add_argument("--engines", default="easyocr,llamaparse")
    ap.add_argument("--book", required=True)
    ap.add_argument("--author", default="")
    ap.add_argument("--subject", default="")
    ap.add_argument("--tier", default="agentic")
    a = ap.parse_args()

    s, _, e = a.pages.partition("-")
    start = int(s)
    end = int(e or s)
    engines = [x.strip() for x in a.engines.split(",") if x.strip()]
    for eng in engines:
        if eng not in ENGINES:
            raise SystemExit(f"알 수 없는 엔진: {eng} (가능: {list(ENGINES)})")

    os.makedirs(PILOT_DIR, exist_ok=True)
    stem = Path(a.pdf).stem
    src_name = os.path.basename(a.pdf)

    rows = []
    for eng in engines:
        print(f"\n===== {eng} : p{start}-{end} =====", flush=True)
        doc = fitz.open(a.pdf)
        t0 = time.time()
        try:
            pages = ENGINES[eng](doc, start, end, tier=a.tier)
        except SystemExit as ex:
            print(f"[{eng}] 건너뜀: {ex}", flush=True)
            rows.append((eng, None, 0.0))
            continue
        finally:
            doc.close()
        dt = round(time.time() - t0, 1)
        out_path = os.path.join(PILOT_DIR, f"{stem}_{eng}_p{start:03d}-{end:03d}.md")
        write_chunk(out_path, eng, a.tier, a.book, a.author, a.subject,
                    src_name, start, end, pages)
        m = metrics(pages)
        rows.append((eng, m, dt))
        print(f"[{eng}] chars={m['chars']} cases={m['cases']} jo={m['jo']} {dt}s → {out_path}",
              flush=True)

    lines = [
        f"# OCR 파일럿 비교 — {a.book} p{start}-{end}", "",
        f"> {src_name} · 생성 {time.strftime('%Y-%m-%d %H:%M')}",
        "> 지표는 1차 신호(추출량·anchor 밀도). 정확도는 korean-law-mcp 검증으로 별도 채점.", "",
        "| 엔진 | 본문글자수 | 사건번호후보 | 조문 | 소요(s) |",
        "|---|---|---|---|---|",
    ]
    for eng, m, dt in rows:
        if m is None:
            lines.append(f"| {eng} | (실패/키없음) | — | — | — |")
        else:
            lines.append(f"| {eng} | {m['chars']} | {m['cases']} | {m['jo']} | {dt} |")
    lines += [
        "", "## 다음 단계",
        "1. 각 엔진 추출본의 사건번호를 korean-law-mcp(search)로 대조 → 정확/위조 채점.",
        "2. 자모혼동 육안 비교(easyocr 기준선 대비).",
        "3. 우승 엔진으로 batch 재추출(출력 outputs/01_ocr_{engine}/, 기존 보존 #16).",
    ]
    cmp_path = os.path.join(PILOT_DIR, f"_compare_{stem}_p{start:03d}-{end:03d}.md")
    with open(cmp_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n[비교표] {cmp_path}", flush=True)
    print("\n".join(lines))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
