# -*- coding: utf-8 -*-
"""Fast unit test: feed the saved LayoutParsingResultV2 JSON through Cell 2's
parser directly, without re-running predict. Proves schema mapping.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
import types
from pathlib import Path

NB_PY = Path(r"H:\내 드라이브\.agent\notebooks\paddle_ocr_pipeline.py")
SAVED_JSON = Path(r"H:\내 드라이브\.agent\notebooks\_dryrun_result.json")

# Stub paddlex / paddleocr so the notebook import doesn't try to load real models
fake_paddlex = types.ModuleType("paddlex")
fake_paddlex.__version__ = "stub"
class _FakeRes:
    def __init__(self, j): self._j = j
    @property
    def json(self): return self._j
class _FakePipeline:
    def __init__(self, payload): self.payload = payload
    def predict(self, *a, **k):
        yield _FakeRes(self.payload)
fake_paddlex.create_pipeline = lambda *a, **k: _FakePipeline({})
sys.modules["paddlex"] = fake_paddlex
fake_paddleocr = types.ModuleType("paddleocr")
fake_paddleocr.PaddleOCR = lambda *a, **k: _FakePipeline({})
sys.modules["paddleocr"] = fake_paddleocr

# Redirect DRIVE_ROOT to a tempdir
TMP = Path(tempfile.mkdtemp(prefix="unit_"))
os.environ["DRIVE_ROOT"] = str(TMP)

# Load notebook source, drop install + the global processing loop + Cell 5
src = NB_PY.read_text(encoding="utf-8")
src = re.sub(
    r"if not os\.path\.exists\(INSTALL_FLAG\):.*?print\(\"패키지 이미 설치됨\. 다음 셀로 진행합니다\.\"\)",
    "print('skip install')", src, flags=re.S,
)
src = src.replace(
    "for book_id in TARGET_BOOKS:\n    print(f\"\\n처리 중: {book_id}\")\n    process_book(book_id, progress[\"books\"][book_id], progress)",
    "TARGET_BOOKS = []  # skipped"
)
src = re.sub(r"# %% \[markdown\]\n# # Cell 5:.*$", "", src, flags=re.S)

nb = types.ModuleType("paddle_ocr_pipeline_unit")
nb.__file__ = str(NB_PY)
nb.__dict__["__name__"] = "__main__"
exec(src, nb.__dict__)

print("\n--- TEST 1: real PaddleX predict result (1 small text block) ---")
real_payload = json.loads(SAVED_JSON.read_text(encoding="utf-8"))
nb._ppstruct = _FakePipeline(real_payload)  # already wrapped with {"res": {...}}
nb._HAS_PADDLEX = True
import numpy as np
fake_arr = np.zeros((10, 10, 3), dtype=np.uint8)
blocks = nb._paddlex_predict(fake_arr)
print(f"got {len(blocks)} blocks")
for b in blocks:
    ct = (b.get("content") or "").replace("\n", " ")[:50]
    print(f"  {b['block_type']:8s} label={b['label']:25} bbox={b['bbox']}  '{ct}'")
assert len(blocks) >= 1
assert blocks[0]["block_type"] in ("text", "title", "table", "figure", "formula")

print("\n--- TEST 2: synthetic fixture covering all label families ---")
synth = {"res": {
    "input_path": "x",
    "page_index": 0, "page_count": 1,
    "width": 800, "height": 1200,
    "model_settings": {},
    "parsing_res_list": [
        {"block_label": "doc_title",       "block_content": "총칙",
         "block_bbox": [10, 10, 700, 60], "block_id": 0, "block_order": 0},
        {"block_label": "paragraph_title", "block_content": "1. 의의",
         "block_bbox": [10, 70, 400, 100], "block_id": 1, "block_order": 1},
        {"block_label": "text",            "block_content": "헌법은 국가의 최고법규이다.\n인권은 천부적이다.",
         "block_bbox": [10, 110, 700, 200], "block_id": 2, "block_order": 2},
        {"block_label": "table",           "block_content": "<table><tr><td>가</td><td>나</td></tr></table>",
         "block_bbox": [10, 210, 700, 350], "block_id": 3, "block_order": 3},
        {"block_label": "image",           "block_content": "",
         "block_bbox": [10, 360, 700, 500], "block_id": 4, "block_order": 4},
        {"block_label": "footnote",        "block_content": "* 주1)",
         "block_bbox": [10, 510, 700, 530], "block_id": 5, "block_order": 5},
        {"block_label": "formula",         "block_content": "E = mc^2",
         "block_bbox": [10, 540, 700, 570], "block_id": 6, "block_order": 6},
    ],
}}
nb._ppstruct = _FakePipeline(synth)
blocks = nb._paddlex_predict(fake_arr)
print(f"got {len(blocks)} blocks")
expect_types = ["title", "title", "text", "table", "figure", "text", "formula"]
for b, want in zip(blocks, expect_types):
    print(f"  label={b['label']:18}  type={b['block_type']:8}  expected={want}  bbox={b['bbox']}")
    assert b["block_type"] == want, f"label {b['label']} expected {want} got {b['block_type']}"

print("\n--- TEST 3: process_page → blocks_to_markdown round-trip ---")
import io as _io
from PIL import Image as _Image
import fitz as _fitz
# Build a temp 1-page PDF
pdf_path = TMP / "tiny.pdf"
doc = _fitz.open()
page = doc.new_page(width=200, height=200)
page.insert_text((20, 50), "hi")
doc.save(str(pdf_path))
doc.close()
nb._ppstruct = _FakePipeline(synth)
blocks = nb.process_page(str(pdf_path), 0)
md = nb.blocks_to_markdown(blocks)
roundtrip = nb._parse_blocks_from_md("<!-- page: 1 source: x -->\n" + md)
print(f"process_page → {len(blocks)} blocks; markdown {len(md)} chars; roundtrip {len(roundtrip)} blocks")
assert len(roundtrip) == len(blocks)
for b, r in zip(blocks, roundtrip):
    assert r["block_id"] == b["block_id"], (r["block_id"], b["block_id"])
    assert r["block_type"] == b["block_type"], (r["block_type"], b["block_type"])

print("\nALL UNIT TESTS PASS")
import shutil; shutil.rmtree(TMP, ignore_errors=True)
