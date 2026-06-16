import fitz

pdf_path = r"H:\내 드라이브\리퀴드텍스트 참조\계약.pdf"
doc = fitz.open(pdf_path)

# Find a page with drawings and print details
found = False
for page_num in range(len(doc)):
    page = doc[page_num]
    drawings = page.get_drawings()
    if drawings:
        print(f"Page {page_num+1} has {len(drawings)} drawings.")
        found = True
        # Print details of the first 10 drawings
        for idx, draw in enumerate(drawings[:10]):
            print(f"  Drawing {idx+1}:")
            print(f"    Type: {draw.get('type')}")
            print(f"    Rect: {draw.get('rect')}")
            print(f"    Fill: {draw.get('fill')}")
            print(f"    Color: {draw.get('color')}")
            # check items inside drawing dict
            items = list(draw.keys())
            print(f"    Keys: {items}")
            rect = draw.get('rect')
            if rect:
                text = page.get_text("text", clip=rect)
                print(f"    Extracted Text: {repr(text.strip())}")
        break

if not found:
    print("No drawings found in the PDF.")
doc.close()
