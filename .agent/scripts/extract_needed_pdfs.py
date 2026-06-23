import os
import sys
import io
from pathlib import Path
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

# Add H:\내 드라이브\.agent\scripts to sys.path so we can import code_pdf_extract_2026-04-30
sys.path.append(str(Path(vp(".agent", "scripts"))))
try:
    import code_pdf_extract_2026_04_30 as extractor
except ImportError:
    # Handle filename differences
    sys.path.append(str(Path(vp(".agent", "scripts"))))
    # Import as module if file has different name format
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "extractor",
        vp(".agent", "scripts", "code_pdf_extract_2026-04-30.py")
    )
    extractor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extractor)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

dir_path = Path(vp("작업용"))
out_dir = Path(vp("outputs", "01_ocr"))
os.makedirs(out_dir, exist_ok=True)

targets = [
    {
        "pdf": "2026 표준판례 반영 헌법 핵심정리 300 - 각종 국가고시 대비, 제3전정4판,_3c_r6_d2.pdf",
        "prefix": "헌법핵심정리300",
        "subject": "공법",
        "author": "금동흠",
        "book": "헌법 핵심정리 300"
    },
    {
        "pdf": "송영곤_사례연습_채권_26.pdf",
        "prefix": "송영곤_사례연습_채권_26",
        "subject": "민사",
        "author": "송영곤",
        "book": "송영곤 사례연습 채권 26"
    },
    {
        "pdf": "송영곤_사례연습_민총_26.pdf",
        "prefix": "송영곤_사례연습_민총_26",
        "subject": "민사",
        "author": "송영곤",
        "book": "송영곤 사례연습 민총 26"
    },
    {
        "pdf": "송영곤_사례연습_물권_26.pdf",
        "prefix": "송영곤_사례연습_물권_26",
        "subject": "민사",
        "author": "송영곤",
        "book": "송영곤 사례연습 물권 26"
    },
    {
        "pdf": "송영곤_사례연습_담보_26.pdf",
        "prefix": "송영곤_사례연습_담보_26",
        "subject": "민사",
        "author": "송영곤",
        "book": "송영곤 사례연습 담보 26"
    },
    {
        "pdf": "송영곤_사례연습_가족_26.pdf",
        "prefix": "송영곤_사례연습_가족_26",
        "subject": "민사",
        "author": "송영곤",
        "book": "송영곤 사례연습 가족 26"
    }
]

print("Starting batch PDF text extraction process...")
print(f"Output directory: {out_dir}")
print("-" * 60)

for t in targets:
    pdf_path = dir_path / t["pdf"]
    if not pdf_path.exists():
        print(f"[MISSING] {t['pdf']} does not exist in {dir_path}")
        continue
    
    print(f"[START] Extracting {t['pdf']} -> prefix: {t['prefix']}...")
    try:
        res = extractor.chunk_pdf(
            str(pdf_path),
            str(out_dir),
            prefix=t["prefix"],
            subject=t["subject"],
            author=t["author"],
            book=t["book"],
            chunk_size=30
        )
        print(f"[SUCCESS] Status: {res.get('status')}, Chunks written: {res.get('chunks')}")
    except Exception as e:
        print(f"[ERROR] Failed to extract {t['pdf']}: {e}")
    print()

print("-" * 60)
print("Batch PDF text extraction process finished.")
