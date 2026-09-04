# -*- coding: utf-8 -*-
"""Dryrun for Cell 2 logic — extract a single PDF page with PP-StructureV3.

Strategy:
1. Rasterize page FIRST while RAM is free (8.7MB malloc was failing
   when pymupdf ran AFTER 13 PaddleX models were loaded).
2. Then load the pipeline and predict.
3. Inspect every shape of the result we might use.
"""
from __future__ import annotations

import io
import os
import sys
import json
import gc
from pathlib import Path

import numpy as np
import fitz
from PIL import Image

PDF_PATH = Path(r"H:\내 드라이브\sync\_교재원문\헌법\변사기_헌법\2025_헌법_변사기.pdf")
PAGE_NUM = 0
DPI = 120  # was 200 → halved to fit on CPU box

print(f"[1] PDF: {PDF_PATH}  exists={PDF_PATH.exists()}")
assert PDF_PATH.exists(), "PDF not found"


def pdf_page_to_image(pdf_path, page_num, dpi=DPI):
    doc = fitz.open(str(pdf_path))
    pix = doc[page_num].get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()
    return img


print(f"[2] rasterize page {PAGE_NUM + 1} at dpi={DPI} BEFORE pipeline load ...")
img = pdf_page_to_image(PDF_PATH, PAGE_NUM, dpi=DPI)
arr = np.array(img)
print(f"    image shape: {arr.shape}  ({arr.nbytes / 1024 / 1024:.1f} MB)")
del img
gc.collect()

print("[3] paddlex import + create_pipeline (mobile config) ...")
import paddlex  # noqa: E402
print(f"    paddlex {paddlex.__version__}")
from paddlex import create_pipeline  # noqa: E402
# 로컬 7.7GB RAM 박스에서 server 모델은 OOM → mobile 변형으로 스왑한 yaml 사용
ppstruct = create_pipeline(
    pipeline=str(Path(__file__).with_name("_pp_structurev3_mobile.yaml")),
)
print("    pipeline OK")

print("[4] predict (seal/formula/chart OFF for CPU memory) ...")
sys.stdout.flush()
results = list(ppstruct.predict(
    arr,
    use_seal_recognition=False,
    use_formula_recognition=False,
    use_chart_recognition=False,
))
print(f"    got {len(results)} result objects")
sys.stdout.flush()

for i, res in enumerate(results):
    print(f"    --- result {i} ---")
    print(f"    type: {type(res).__name__}")
    attrs = [a for a in dir(res) if not a.startswith("_")]
    print(f"    attrs ({len(attrs)}): {attrs[:40]}")

    # json
    try:
        if hasattr(res, "json"):
            j = res.json
            j = j() if callable(j) else j
            keys = list(j.keys()) if isinstance(j, dict) else type(j).__name__
            print(f"    json keys: {keys}")
            outp = Path(r"H:\내 드라이브\.agent\notebooks\_dryrun_result.json")
            with open(outp, "w", encoding="utf-8") as f:
                json.dump(j, f, ensure_ascii=False, indent=2, default=str)
            print(f"    saved -> {outp}")
    except Exception as e:
        print(f"    json error: {type(e).__name__}: {e}")

    # markdown attribute
    try:
        if hasattr(res, "markdown"):
            md = res.markdown
            print(f"    markdown attr type: {type(md).__name__}")
            if isinstance(md, dict):
                print(f"    markdown keys: {list(md.keys())}")
                txt = (
                    md.get("markdown_texts")
                    or md.get("markdown")
                    or md.get("text")
                )
                if txt:
                    out_md = Path(r"H:\내 드라이브\.agent\notebooks\_dryrun_page.md")
                    out_md.write_text(str(txt)[:8000], encoding="utf-8")
                    print(f"    saved markdown -> {out_md} ({len(str(txt))} chars)")
    except Exception as e:
        print(f"    markdown error: {type(e).__name__}: {e}")

    # save_to_markdown convenience
    try:
        if hasattr(res, "save_to_markdown"):
            out_dir = Path(r"H:\내 드라이브\.agent\notebooks\_dryrun_save")
            out_dir.mkdir(exist_ok=True)
            res.save_to_markdown(str(out_dir))
            print(f"    save_to_markdown -> {out_dir}")
            for p in out_dir.rglob("*"):
                print(f"      {p.name}  ({p.stat().st_size if p.is_file() else 'dir'})")
    except Exception as e:
        print(f"    save_to_markdown error: {type(e).__name__}: {e}")

print("[5] DONE")
