import sys
import os
import io

sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
import pypdfium2 as pdfium

PDF_PATH = Path(r"H:\내 드라이브\sync\_교재원문\헌법\변사기_헌법\2025_헌법_변사기.pdf")
OUT_IMG = Path(r"C:\pdocr\page1.png")

print(f"[1] Rendering PDF page 1 -> {OUT_IMG}")
pdf = pdfium.PdfDocument(str(PDF_PATH))
page = pdf[0]
pil_image = page.render(scale=2.0).to_pil()
pil_image.save(str(OUT_IMG))
print(f"    Image saved, size={pil_image.size}")
pdf.close()

print("[2] Initializing PaddleOCR (lang=korean, defaults)")
from paddleocr import PaddleOCR
ocr = PaddleOCR(
    lang='korean',
    use_textline_orientation=True,
)

print("[3] Running OCR on page 1 (predict)...")
result = list(ocr.predict(str(OUT_IMG)))

print("[4] Result type:", type(result))
print("[4] Result preview:")

# PaddleOCR 3.x returns list of OCRResult objects (dict-like)
if isinstance(result, list) and len(result) > 0:
    first = result[0]
    print(f"    first item type: {type(first)}")
    # Try dict-style (3.x)
    if hasattr(first, 'get') or isinstance(first, dict):
        texts = first.get('rec_texts', None) if hasattr(first, 'get') else None
        if texts is None and isinstance(first, dict):
            texts = first.get('rec_texts', [])
        if texts:
            print("    First 10 lines:")
            for t in texts[:10]:
                print(f"      - {t}")
        else:
            print(f"    keys: {list(first.keys()) if hasattr(first, 'keys') else 'n/a'}")
    else:
        # Old API: list of [bbox, (text, conf)]
        print("    First 10 lines (old API):")
        items = first if isinstance(first, list) else result
        for line in items[:10]:
            try:
                txt = line[1][0]
                conf = line[1][1]
                print(f"      - [{conf:.2f}] {txt}")
            except Exception:
                print(f"      - {line}")

print("[5] Done.")
