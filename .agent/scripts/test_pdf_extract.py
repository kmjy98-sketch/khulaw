import fitz  # PyMuPDF
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

pdf_paths = [
    r"H:\내 드라이브\3.공법\_분할\유니온헌법기출편_03_통치구조_국회_대통령.pdf",
    r"H:\내 드라이브\3.공법\_분할\유니온헌법기출편_04_법원_헌법재판소.pdf"
]

for path in pdf_paths:
    print(f"=== {path} ===")
    try:
        doc = fitz.open(path)
        print(f"Total pages: {len(doc)}")
        for i in range(min(5, len(doc))):
            print(f"--- Page {i+1} ---")
            text = doc[i].get_text("text")
            print(text[:1000])
    except Exception as e:
        print(f"Error opening {path}: {e}")
