import os
import pypdf
import sys

sys.stdout.reconfigure(encoding='utf-8')

pdf_files = {
    "핵정_헌재": "H:/내 드라이브/3.공법/_분할/핵심정리300_01_헌법재판.pdf",
    "핵정_총론": "H:/내 드라이브/3.공법/_분할/핵심정리300_03_기본권_나머지_헌법총론.pdf",
    "핵정_통치": "H:/내 드라이브/3.공법/_분할/핵심정리300_04_통치구조.pdf",
    "유니온_통치": "H:/내 드라이브/3.공법/_분할/유니온헌법기출편_03_통치구조_국회_대통령.pdf",
    "유니온_헌재": "H:/내 드라이브/3.공법/_분할/유니온헌법기출편_04_법원_헌법재판소.pdf",
    "해커스_헌재": "H:/내 드라이브/3.공법/_분할/2027해커스헌법사례형_01_헌법재판.pdf",
    "해커스_통치": "H:/내 드라이브/3.공법/_분할/2027해커스헌법사례형_03_헌법총론_통치구조.pdf"
}

for name, path in pdf_files.items():
    print(f"\n==================== {name} ====================")
    if not os.path.exists(path):
        print("Not found")
        continue
    try:
        with open(path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            # Search first 20 pages
            for idx in range(min(20, len(reader.pages))):
                text = reader.pages[idx].extract_text()
                # Check if it looks like a TOC page
                if "차례" in text or "목차" in text or "Theme" in text or "CONTENTS" in text or "CONTENTS" in text.upper():
                    print(f"-> Probable TOC Page: {idx+1}")
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    for line in lines[:30]:  # print first 30 lines
                        print(f"   {line}")
    except Exception as e:
        print(f"Error: {e}")
