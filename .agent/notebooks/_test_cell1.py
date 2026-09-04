"""Cell 1 의 detect_toc_offset 와 scan_books 동작 테스트.

ocr_extract_v2.py 를 import 하지 않고 (Cell 0a 가 colab 의존이므로) 핵심 함수만
복사하지 않고 소스에서 추출 실행해서 동작을 확인한다.

테스트 PDF: sync/_교재원문/헌법/변사기_헌법/2025_헌법_변사기.pdf (현재 유일한 PDF)
"""
from __future__ import annotations

import os
import sys
import json
import re
import glob
from datetime import datetime

# pymupdf
import fitz

DRIVE_ROOT = r"H:\내 드라이브"
SOURCE_DIR = os.path.join(DRIVE_ROOT, "sync", "_교재원문")
STATE_DIR = os.path.join(DRIVE_ROOT, ".auto-memory", "ocr_state_TEST")
os.makedirs(STATE_DIR, exist_ok=True)
OFFSET_TABLE_PATH = os.path.join(STATE_DIR, "offset_table.json")

# === 노트북 Cell 1 의 함수들 (그대로 복사) ===
_ROMAN_RE = re.compile(r"^\s*([ivxlcdm]{1,5})\s*$", re.IGNORECASE)
_ARABIC_RE = re.compile(r"^\s*(\d{1,4})\s*$")
_ROMAN_VALID = {
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
    "xxi", "xxii", "xxiii", "xxiv", "xxv", "xxvi", "xxvii", "xxviii", "xxix", "xxx",
}


def _classify_pagenum(page_text: str) -> str:
    if not page_text:
        return "none"
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    tail = lines[-8:]
    for ln in reversed(tail):
        m = _ARABIC_RE.match(ln)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 1500:
                return "arabic"
        m = _ROMAN_RE.match(ln)
        if m and m.group(1).lower() in _ROMAN_VALID:
            return "roman"
    return "none"


def detect_toc_offset(pdf_path: str, max_scan: int = 50) -> tuple[int, str]:
    doc = fitz.open(pdf_path)
    try:
        n_scan = min(max_scan, doc.page_count)
        labels: list[str] = []
        for i in range(n_scan):
            try:
                txt = doc.load_page(i).get_text("text")
            except Exception:
                txt = ""
            labels.append(_classify_pagenum(txt))
        has_roman = any(l == "roman" for l in labels)
        if has_roman:
            last_roman = max(i for i, l in enumerate(labels) if l == "roman")
            for j in range(last_roman + 1, len(labels)):
                if labels[j] == "arabic":
                    return j, "auto"
            return 0, "fallback"
        return 0, "fallback"
    finally:
        doc.close()


def _book_name_from_path(pdf_path: str) -> str:
    rel = os.path.relpath(pdf_path, SOURCE_DIR)
    parts = rel.replace("\\", "/").split("/")
    stem = os.path.splitext(parts[-1])[0]
    if len(parts) >= 2:
        folder = parts[-2]
        if folder == stem:
            return stem
        return f"{folder}__{stem}"
    return stem


def main():
    pdfs = sorted(glob.glob(os.path.join(SOURCE_DIR, "**", "*.pdf"), recursive=True))
    print(f"PDFs found: {len(pdfs)}")
    for p in pdfs:
        rel = os.path.relpath(p, DRIVE_ROOT)
        name = _book_name_from_path(p)
        try:
            doc = fitz.open(p)
            total = doc.page_count
            doc.close()
        except Exception as e:
            print(f"  [open fail] {rel}: {e}")
            continue

        # 디버깅: 처음 30 페이지 라벨 시퀀스 출력
        doc = fitz.open(p)
        try:
            n = min(30, total)
            seq = []
            for i in range(n):
                t = doc.load_page(i).get_text("text")
                seq.append(_classify_pagenum(t))
        finally:
            doc.close()

        offset, method = detect_toc_offset(p)
        print(f"\n=== {name} ===")
        print(f"  rel        : {rel}")
        print(f"  total_pages: {total}")
        print(f"  toc_offset : {offset}")
        print(f"  method     : {method}")
        print(f"  label seq  : {seq}")

        # raw 페이지 번호 텍스트 (마지막 줄) 표본
        doc = fitz.open(p)
        try:
            for idx in [0, 5, 10, 15, 20, 25]:
                if idx >= total:
                    continue
                t = doc.load_page(idx).get_text("text")
                tail = [ln.strip() for ln in t.splitlines() if ln.strip()][-3:]
                print(f"  page {idx+1:3d} tail: {tail}")
        finally:
            doc.close()


if __name__ == "__main__":
    main()
