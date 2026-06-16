#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""서보학 PDF OCR 품질 테스트 (1~2 페이지)"""
import sys, time
from pathlib import Path
import fitz

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PDF = Path("2.형사/20.서보학_형법1/교재/서보학_형법총론_18.pdf")

print("[1] easyocr Reader 로드 (최초 1회 모델 다운로드 발생)...")
t0 = time.time()
import easyocr
reader = easyocr.Reader(['ko', 'en'], gpu=False, verbose=False)
print(f"  loaded in {time.time()-t0:.1f}s")

print(f"\n[2] PDF 열기: {PDF}")
doc = fitz.open(str(PDF))
print(f"  pages: {len(doc)}")

# Test pages: 본문 시작 추정 (목차 이후)
test_pages = [50, 100, 200]

for pno in test_pages:
    print(f"\n--- Page {pno+1} ---")
    page = doc[pno]
    # Render @ 200 DPI
    t0 = time.time()
    pix = page.get_pixmap(dpi=200)
    img_bytes = pix.tobytes("png")
    t_render = time.time() - t0

    t0 = time.time()
    result = reader.readtext(img_bytes, detail=0, paragraph=True)
    t_ocr = time.time() - t0

    text = "\n".join(result)
    print(f"render: {t_render:.1f}s | ocr: {t_ocr:.1f}s | chars: {len(text)}")
    print("---first 500 chars---")
    print(text[:500])
    print("---")
