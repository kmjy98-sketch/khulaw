# -*- coding: utf-8 -*-
"""Dryrun for Cell 3 (compare_and_diff) using synthetic Paddle blocks.

Validates:
- Block parser handles new schema markers (text/table/title/figure).
- Title blocks are included in text-block aggregation for diff.
- Table blocks generate `table_adopt` corrections with original_content.
- Text conflicts generate `text_conflict` corrections per differing line.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

NB = Path(r"H:\내 드라이브\.agent\notebooks\paddle_ocr_pipeline.py")
SRC = NB.read_text(encoding="utf-8")

# Drop Cell 0a (pip install runs)
SRC = re.sub(r"if not os\.path\.exists\(INSTALL_FLAG\):.*?print\(\"패키지 이미 설치됨\. 다음 셀로 진행합니다\.\"\)",
             "print('skip install')", SRC, flags=re.S)

# Stub out heavy imports + pipeline init
PATCH = r'''
class _Stub:
    def __init__(self, *a, **k): pass
    def predict(self, *a, **k):  return []
import types
fake = types.ModuleType("paddleocr")
fake.PaddleOCR = _Stub
sys.modules["paddleocr"] = fake
fake_paddlex = types.ModuleType("paddlex")
fake_paddlex.__version__ = "stub"
fake_paddlex.create_pipeline = lambda *a, **k: _Stub()
sys.modules["paddlex"] = fake_paddlex
'''
SRC = SRC.replace("import paddlex\nprint(f\"PaddleX:", PATCH + "\nimport paddlex\nprint(f\"PaddleX:")

# Set DRIVE_ROOT to a tempdir we control + skip Colab branch
TMP = Path(tempfile.mkdtemp(prefix="cell3test_"))
print(f"TMP DRIVE_ROOT: {TMP}")
os.environ["DRIVE_ROOT"] = str(TMP)

# Skip Cell 2 processing loop entirely — we'll inject paddle_dir + chunks manually
SRC = SRC.replace(
    "for book_id in TARGET_BOOKS:\n    print(f\"\\n처리 중: {book_id}\")\n    process_book(book_id, progress[\"books\"][book_id], progress)",
    "TARGET_BOOKS = []  # skipped in dryrun"
)

# Skip the final stats loop in Cell 5 — we'll inspect ourselves
SRC = re.sub(r"# %% \[markdown\]\n# # Cell 5:.*$", "", SRC, flags=re.S)

# --- Build fake paddle dir + chunk MD ---
SYNC = TMP / "sync" / "_교재원문"
BOOK_ID = "test_book"
PADDLE = SYNC / BOOK_ID / "_paddle"
PADDLE.mkdir(parents=True, exist_ok=True)

# Original chunk MD has a markdown table + body text
CHUNK = SYNC / "test_book_p001-001.md"
CHUNK.write_text(
    "# 헌법총론 제1장\n"
    "\n"
    "헌법은 국가의 최고법규이다.\n"
    "기본권은 인간의 본성에서 유래한다.\n"
    "\n"
    "| 종류 | 내용 |\n"
    "|------|------|\n"
    "| 자유권 | 신체의 자유 |\n"
    "| 사회권 | 인간다운 생활 |\n"
    "\n"
    "헌법재판소는 위헌법률심판을 담당한다.\n",
    encoding="utf-8",
)

# Paddle output for page 1: title + text (with one OCR diff) + table (HTML form)
P1 = PADDLE / "p0001.md"
P1.write_text(
    "<!-- page: 1 source: test_book -->\n"
    "<!-- block: p1-b00 type: title bbox: [0,0,100,20] -->\n"
    "헌법총론 제1장\n"
    "<!-- block: p1-b01 type: text bbox: [0,30,100,80] -->\n"
    "헌법은 국가의 최고법규이다.\n"
    "기본권은 인간의 본성에서 유래한다.\n"
    "<!-- block: p1-b02 type: table bbox: [0,90,100,180] -->\n"
    "| 종류 | 내용 |\n"
    "|------|------|\n"
    "| 자유권 | 신체의 자유 |\n"
    "| 사회권 | 사람다운 생활 |\n"  # NOTE: '인간' vs '사람' diff
    "<!-- block: p1-b03 type: text bbox: [0,200,100,220] -->\n"
    "헌법재판소는 위헌법률심판을 담당한다.\n",
    encoding="utf-8",
)

# Pre-seed progress.json so the diff loop targets our book
mem = TMP / ".auto-memory"
mem.mkdir(exist_ok=True)
(mem / "ocr_progress.json").write_text(json.dumps({
    "version": "1.0",
    "books": {
        BOOK_ID: {
            "pdf_path": str(SYNC / "doesnotexist.pdf"),
            "subject": "test",
            "status": "ocr_done",
            "pages_done": [1],
            "in_progress_chunk": 1,
            "paddle_dir": str(PADDLE),
            "md_chunks": [{"path": str(CHUNK), "start": 1, "end": 1}],
        }
    },
}, ensure_ascii=False), encoding="utf-8")

# Run the patched notebook source as a single module
glb = {"__name__": "__main__", "__file__": str(NB)}
exec(SRC, glb)

# Read corrections
corr_dir = TMP / ".auto-memory" / "corrections"
print(f"\n--- corrections in {corr_dir} ---")
for f in corr_dir.glob("*.jsonl"):
    print(f"FILE: {f.name}")
    for line in f.read_text(encoding="utf-8").splitlines():
        c = json.loads(line)
        print(f"  {c.get('type'):14}  block_id={c.get('block_id', '-')}  ", end="")
        if c.get("type") == "table_adopt":
            tp = c.get("table_position")
            ocp = (c.get("original_content") or "").replace("\n", " | ")[:60]
            print(f"pos={tp}  orig='{ocp}'")
        elif c.get("type") == "text_conflict":
            print(f"line={c.get('line_idx')}  orig='{c.get('original')}'  paddle='{c.get('paddle')}'")
        else:
            print()

print("\nDryrun cell3 OK")
shutil.rmtree(TMP, ignore_errors=True)
