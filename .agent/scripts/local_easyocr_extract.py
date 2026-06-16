#!/usr/bin/env python
"""로컬 easyocr 이미지 OCR — 스캔 PDF 재추출 (CPU), 2026-06-01

목적:
- code_pdf_extract(PyMuPDF 텍스트레이어 덤프)의 ①②③→O/0 손상을 회피.
- 스캔 이미지 PDF를 *페이지 이미지*로 추출 → easyocr(ko,en) 이미지 OCR.

주의:
- easyocr CPU는 자모혼동 오류(를/름·는/눈·을/올·훼/웨) + 조문 띄어쓰기 오류가 있음.
- 따라서 출력은 '01 OCR 미교정' 단계이며, 후속 Claude 교정(#13 3단계) + korean-law-mcp(조문·판례) 검증 필수.
- 02-wiki(속성·callout·헤더 위계)는 이 다음 LLM 단계에서 수행 (이 스크립트는 OCR만).

사용:
  python local_easyocr_extract.py --pdf <PDF> --out <DIR> --prefix <P> \
    --book "<책명>" --author "<저자>" --subject "<과목>" [--chunk-size 30] [--start 1] [--end 0]
"""
import os
import sys
import io
import time
import json
import argparse
from pathlib import Path
from datetime import datetime

import fitz  # PyMuPDF (렌더/이미지 추출 전용 — 텍스트레이어 사용 안 함)
from PIL import Image
import numpy as np


def page_image(page, doc, dpi=250):
    """페이지의 풀페이지 임베드 이미지(원해상도) 우선, 없으면 렌더."""
    imgs = page.get_images(full=True)
    if imgs:
        big = max(imgs, key=lambda im: im[2] * im[3])
        if big[2] >= 1000 and big[3] >= 1400:
            base = doc.extract_image(big[0])
            return Image.open(io.BytesIO(base["image"])).convert("RGB")
    pix = page.get_pixmap(dpi=dpi)
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--book", required=True)
    ap.add_argument("--author", default="")
    ap.add_argument("--subject", default="")
    ap.add_argument("--chunk-size", type=int, default=30)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=0)  # 0 = 마지막 페이지
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)

    import easyocr
    print("[easyocr] 모델 로드(ko,en, CPU)...", flush=True)
    t0 = time.time()
    reader = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)
    print(f"[easyocr] 로드 완료 {time.time()-t0:.1f}s", flush=True)

    doc = fitz.open(a.pdf)
    total = doc.page_count
    end = a.end or total
    print(f"[PDF] {os.path.basename(a.pdf)} 총 {total}p, 처리 {a.start}-{end}", flush=True)

    log = []
    page = a.start
    while page <= end:
        ce = min(page + a.chunk_size - 1, end)
        out_path = os.path.join(a.out, f"{a.prefix}_p{page:03d}-{ce:03d}.md")
        if os.path.exists(out_path) and os.path.getsize(out_path) > 200:
            print(f"[SKIP 존재] {out_path}", flush=True)
            page = ce + 1
            continue

        parts = []
        for i in range(page - 1, ce):
            ts = time.time()
            img = page_image(doc[i], doc)
            res = reader.readtext(np.array(img), detail=0, paragraph=True)
            txt = "\n".join(res).strip()
            parts.append(f"<!-- p.{i+1} -->\n\n{txt}")
            dt = round(time.time() - ts, 1)
            log.append({"page": i + 1, "chars": len(txt), "sec": dt})
            print(f"  p{i+1}: {len(txt)}자 {dt}s", flush=True)

        body = "\n\n".join(parts)
        fm = (
            "---\n"
            f"tags: [교재원문, {a.subject}, {a.author}_{a.book}]\n"
            f"교재: 《{a.book}》 ({a.author})\n"
            f"과목: {a.subject}\n"
            f"포함_페이지: {page}-{ce}\n"
            f"저자: {a.author}\n"
            f"출처: {os.path.basename(a.pdf)}\n"
            f"추출일: {datetime.now():%Y-%m-%d}\n"
            "추출엔진: easyocr-CPU(ko,en) [이미지 OCR]\n"
            "교정상태: 미교정 — 자모혼동(를/름·는/눈·을/올·훼/웨)·조문띄어쓰기 가능, Claude 교정+korean-law-mcp 검증 필요\n"
            "---\n"
        )
        title = f"# {a.book} ({a.author}) — p.{page}-{ce} [easyocr 미교정]\n"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(fm + "\n" + title + "\n" + body + "\n")
        print(f"[WROTE] {out_path}", flush=True)
        page = ce + 1

    json.dump(log, open(os.path.join(a.out, f"{a.prefix}_ocrlog.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    if log:
        avg = sum(x["sec"] for x in log) / len(log)
        print(f"DONE {len(log)}p, 평균 {avg:.1f}s/p", flush=True)
    else:
        print("DONE (처리 페이지 없음)", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
