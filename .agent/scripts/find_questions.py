import fitz  # PyMuPDF
import sys
import io
import re
import os  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

pdf_paths = {
    "03_국회_대통령": vp("3.공법", "_분할", "유니온헌법기출편_03_통치구조_국회_대통령.pdf"),
    "04_법원_헌법재판소": vp("3.공법", "_분할", "유니온헌법기출편_04_법원_헌법재판소.pdf")
}

target_nums = [
    1, 5, 6, 7, 8, 12, 13, 14, 15, 16, 17, 21, 24, 26, 27, 28, 32, 33, 39, 44, 45, 49, 51, 52, 58, 59, 61, 66, 67, 68,
    77, 78, 79, 80, 83, 84, 85, 86, 87, 88, 90, 91, 98, 99, 100, 107, 108, 109, 110, 111, 112, 113, 114, 130, 133, 134,
    140, 141, 142, 150, 151, 152, 155
]

# We will search for variations of "문 X" where X is the target number.
# In PDF, OCR might read "문7", "문 7", "홉 문7", "뚫 문7", "뽑 문7", etc.
for name, path in pdf_paths.items():
    print(f"\n===== Searching in {name} =====")
    try:
        doc = fitz.open(path)
        for page_idx in range(len(doc)):
            text = doc[page_idx].get_text("text")
            
            # Find all patterns of numbers
            matches = re.finditer(r'(?:문||뽑|홉|뚫|띔|물)\s*(\d+)', text)
            for m in matches:
                num = int(m.group(1))
                if num in target_nums:
                    # Print around the match to verify
                    start = max(0, m.start() - 20)
                    end = min(len(text), m.end() + 100)
                    snippet = text[start:end].replace('\n', ' ')
                    print(f"Page {page_idx+1} | Found 문{num}: {snippet}")
    except Exception as e:
        print(f"Error reading {name}: {e}")
