import fitz
import sys

pdf_path = r"H:\내 드라이브\리퀴드텍스트 참조\계약.pdf"
doc = fitz.open(pdf_path)

print(f"Total pages: {len(doc)}")

found_annots = 0
for page_num in range(len(doc)):
    page = doc[page_num]
    annots = list(page.annots()) if page.annots() else []
    if annots:
        for annot in annots:
            found_annots += 1
            # annot.type is a tuple (number, name) in newer PyMuPDF, or just a dict/number. 
            # Let's print the representation of annot.type and details
            annot_type = annot.type
            rect = annot.rect
            print(f"Page {page_num+1}: Type={annot_type}, Rect={rect}")
            
            # Extract text within the annotation rectangle
            text = page.get_text("text", clip=rect)
            print(f"  Extracted Text: {repr(text.strip())}")
            if found_annots >= 10:
                print("Printed 10 annotations. Stopping check.")
                doc.close()
                sys.exit(0)

if found_annots == 0:
    print("No annotations found in the PDF.")
doc.close()
