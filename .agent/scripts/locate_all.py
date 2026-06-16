import fitz
import sys
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

pdf_paths = {
    "03_국회_대통령": r"H:\내 드라이브\3.공법\_분할\유니온헌법기출편_03_통치구조_국회_대통령.pdf",
    "04_법원_헌법재판소": r"H:\내 드라이브\3.공법\_분할\유니온헌법기출편_04_법원_헌법재판소.pdf"
}

target_nums = [
    1, 5, 6, 7, 8, 12, 13, 14, 15, 16, 17, 21, 24, 26, 27, 28, 32, 33, 39, 44, 45, 49, 51, 52, 58, 59, 61, 66, 67, 68,
    77, 78, 79, 80, 83, 84, 85, 86, 87, 88, 90, 91, 98, 99, 100, 107, 108, 109, 110, 111, 112, 113, 114, 130, 133, 134,
    140, 141, 142, 150, 151, 152, 155
]

print("Loading PDFs...")
pages_text = {}
for name, path in pdf_paths.items():
    try:
        doc = fitz.open(path)
        pages_text[name] = [doc[i].get_text("text") for i in range(len(doc))]
        print(f"Loaded {name}: {len(doc)} pages")
    except Exception as e:
        print(f"Error loading {name}: {e}")

print("\nSearching...")
# We want to identify the exact page where each question starts.
# A question page typically contains "[question number] X년 변호사시험" or "[question number] X년 사법시험" or similar.
# Let's map target questions to the files and page indices.
results = {}
for num in target_nums:
    found = []
    # Broaden regex to find OCR anomalies for "문 X" at the start of a line or within headers
    # Like "문X", "문 X", "홉 문X", "뽑 문X", "뚫 문X", "띔 문X"
    # Also sometimes OCR reads "문" as "물" or "봅" or "듭"
    pattern = re.compile(rf'(?:문|물|띔|뚫|홉|뽑|쿱|듭|뽑\s*문|홉\s*문|뚫\s*문)\s*{num}\b')
    for file_name, pages in pages_text.items():
        for p_idx, text in enumerate(pages):
            for m in pattern.finditer(text):
                # Check context to see if it's the start of the question (e.g. includes "년 변호사시험" or "변시" or is a title)
                start = max(0, m.start() - 20)
                end = min(len(text), m.end() + 150)
                snippet = text[start:end].replace('\n', ' ')
                found.append((file_name, p_idx + 1, snippet))
    results[num] = found

for num in target_nums:
    matches = results.get(num, [])
    if not matches:
        print(f"문{num}: NOT FOUND")
    else:
        print(f"문{num}: found {len(matches)} matches")
        for file_name, page_num, snippet in matches[:2]:
            print(f"  - {file_name} P.{page_num}: {snippet}")
