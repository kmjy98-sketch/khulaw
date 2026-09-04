# -*- coding: utf-8 -*-
"""End-to-end dryrun of the notebook Cell 2 _paddlex_predict on a real PDF page.

Loads the production notebook .py module, monkeypatches `_ppstruct` to use the
mobile-model pipeline (so it fits in 7.7GB RAM), then runs `process_page` on
page 1 of the test PDF and verifies the returned blocks.
"""
from __future__ import annotations

import io
import os
import sys
import json
import gc
import re
import types
from pathlib import Path

import numpy as np
import fitz
from PIL import Image

PDF_PATH = Path(r"H:\내 드라이브\sync\_교재원문\헌법\변사기_헌법\2025_헌법_변사기.pdf")
NB_PY = Path(r"H:\내 드라이브\.agent\notebooks\paddle_ocr_pipeline.py")
MOBILE_CFG = Path(r"H:\내 드라이브\.agent\notebooks\_pp_structurev3_mobile.yaml")

# Pre-rasterize the page BEFORE loading paddlex (RAM saver)
print(f"[1] rasterize {PDF_PATH.name} page 1 at dpi=120 ...")
doc = fitz.open(str(PDF_PATH))
pix = doc[0].get_pixmap(matrix=fitz.Matrix(120 / 72, 120 / 72))
img = Image.open(io.BytesIO(pix.tobytes("png")))
arr = np.array(img)
doc.close(); del img, pix; gc.collect()
print(f"    image: {arr.shape}")

# Stub Cell 0a (skip pip), redirect DRIVE_ROOT to a tempdir so writes are safe.
# IMPORTANT: pin PADDLE_PDX_CACHE_HOME to the EXISTING cache so we don't
# re-download 13 models into a fresh tempdir every test run.
import tempfile
TMP = Path(tempfile.mkdtemp(prefix="e2e_"))
os.environ["DRIVE_ROOT"] = str(TMP)
os.environ["PADDLE_PDX_CACHE_HOME"] = r"C:\Users\111\.paddlex"
print(f"[2] DRIVE_ROOT redirected to {TMP}")
print(f"    PADDLE_PDX_CACHE_HOME pinned to existing cache")

# Load notebook source, drop Cell 0a install, drop the global processing loop,
# drop Cell 5 stats (we'll inspect manually).
src = NB_PY.read_text(encoding="utf-8")
src = re.sub(
    r"if not os\.path\.exists\(INSTALL_FLAG\):.*?print\(\"패키지 이미 설치됨\. 다음 셀로 진행합니다\.\"\)",
    "print('skip install')", src, flags=re.S,
)
# Force the notebook to use the mobile-model pipeline so it fits in 7.7GB RAM
src = src.replace(
    '_ppstruct = create_pipeline("PP-StructureV3")',
    f'_ppstruct = create_pipeline(pipeline=r"{MOBILE_CFG}")'
)
src = src.replace(
    "for book_id in TARGET_BOOKS:\n    print(f\"\\n처리 중: {book_id}\")\n    process_book(book_id, progress[\"books\"][book_id], progress)",
    "TARGET_BOOKS = []  # skipped",
)
src = re.sub(r"# %% \[markdown\]\n# # Cell 5:.*$", "", src, flags=re.S)

# Run notebook source as a module
nb = types.ModuleType("paddle_ocr_pipeline_e2e")
nb.__file__ = str(NB_PY)
nb.__dict__["__name__"] = "__main__"
print("[3] exec notebook source ...")
exec(src, nb.__dict__)

# Pipeline already constructed with mobile config inside the exec'd notebook
print("[4] pipeline ready (mobile config patched into notebook source)")

# Run the actual function under test
print("[5] _paddlex_predict on page image ...")
blocks = nb._paddlex_predict(arr)
print(f"    -> {len(blocks)} blocks")
for b in blocks[:8]:
    ct = (b.get("content") or "").replace("\n", " ")[:50]
    print(f"      {b.get('block_type'):8s} label={b.get('label'):25} bbox={b.get('bbox')} content='{ct}'")

# Also exercise process_page on a temp PDF page 1
print("[6] process_page (full pipeline path) ...")
blocks2 = nb.process_page(str(PDF_PATH), 0)
print(f"    -> {len(blocks2)} blocks; ids: {[b['block_id'] for b in blocks2[:5]]}")

# Convert to markdown the way Cell 2 does
md = nb.blocks_to_markdown(blocks2)
print(f"[7] blocks_to_markdown produced {len(md)} chars")
out_md = Path(r"H:\내 드라이브\.agent\notebooks\_dryrun_e2e_page1.md")
out_md.write_text(md, encoding="utf-8")
print(f"    saved -> {out_md}")

# Validate parser invariants
parsed = nb._parse_blocks_from_md("<!-- page: 1 source: x -->\n" + md)
print(f"[8] _parse_blocks_from_md round-trips {len(parsed)} blocks "
      f"(expect {len(blocks2)})")
assert len(parsed) == len(blocks2), "Round-trip count mismatch"
print("    OK")

print("\nE2E DRYRUN OK")
