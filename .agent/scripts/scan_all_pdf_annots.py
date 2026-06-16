import fitz
import os

folder_path = r"H:\내 드라이브\리퀴드텍스트 참조"
pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]

for pdf_file in pdf_files:
    pdf_path = os.path.join(folder_path, pdf_file)
    try:
        doc = fitz.open(pdf_path)
        total_annots = 0
        annot_types = {}
        for page_num in range(len(doc)):
            page = doc[page_num]
            annots = page.annots()
            if annots:
                for annot in annots:
                    total_annots += 1
                    t = str(annot.type)
                    annot_types[t] = annot_types.get(t, 0) + 1
        print(f"File: {pdf_file} | Total pages: {len(doc)} | Total Annots: {total_annots} | Types: {annot_types}")
        doc.close()
    except Exception as e:
        print(f"Error reading {pdf_file}: {e}")
