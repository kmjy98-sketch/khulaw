import pypdf
import os

pdf_path = "H:/내 드라이브/3.공법/_분할/핵심정리300_01_헌법재판.pdf"
if not os.path.exists(pdf_path):
    print("File not found")
else:
    with open(pdf_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        print("Total pages:", len(reader.pages))
        for idx in [0, 5, 10, 20]:
            if idx < len(reader.pages):
                text = reader.pages[idx].extract_text()
                print(f"Page {idx+1} text length: {len(text)}")
                print(f"Sample: {text[:200]}")
