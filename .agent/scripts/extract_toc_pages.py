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

os.makedirs("H:/내 드라이브/.agent/temp_toc", exist_ok=True)

for name, path in pdf_files.items():
    print(f"Extracting Tocs for {name}...")
    if not os.path.exists(path):
        print(f"File {path} not found")
        continue
    try:
        with open(path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            # Extract first 8 pages
            toc_text = ""
            for idx in range(min(8, len(reader.pages))):
                toc_text += f"\n--- Page {idx+1} ---\n"
                toc_text += reader.pages[idx].extract_text()
            
            out_path = f"H:/내 드라이브/.agent/temp_toc/{name}_toc.txt"
            with open(out_path, 'w', encoding='utf-8') as out_f:
                out_f.write(toc_text)
            print(f"Saved {out_path}")
    except Exception as e:
        print(f"Error {name}: {e}")
