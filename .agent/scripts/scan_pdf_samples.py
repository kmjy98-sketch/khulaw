import fitz
import os

folder_path = r"H:\내 드라이브\리퀴드텍스트 참조"
pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]

for pdf_file in pdf_files:
    pdf_path = os.path.join(folder_path, pdf_file)
    try:
        doc = fitz.open(pdf_path)
        print(f"\nAnalyzing: {pdf_file} (Pages: {len(doc)})")
        
        pages_to_check = min(5, len(doc))
        text_samples = []
        drawing_count = 0
        highlights_found = 0
        
        for page_num in range(pages_to_check):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:
                text_samples.append(f"P{page_num+1}: {text[:100]}...")
            
            drawings = page.get_drawings()
            drawing_count += len(drawings)
            
            for draw in drawings:
                fill = draw.get('fill')
                fill_opacity = draw.get('fill_opacity')
                if fill_opacity is None:
                    fill_opacity = 1.0
                
                is_hi = False
                if fill:
                    r, g, b = fill
                    if r > 0.8 and g > 0.8 and b < 0.6:
                        is_hi = True
                    elif r < 0.6 and g > 0.8 and b < 0.6:
                        is_hi = True
                    elif r < 0.6 and g > 0.6 and b > 0.8:
                        is_hi = True
                    elif r > 0.8 and g < 0.6 and b > 0.8:
                        is_hi = True
                
                if fill_opacity < 0.95:
                    is_hi = True
                    
                if is_hi:
                    highlights_found += 1
                    if highlights_found <= 3:
                        rect = draw.get('rect')
                        txt = page.get_text("text", clip=rect).strip()
                        print(f"  [Found Highlight Candidate] Page {page_num+1}: Rect={rect}, Fill={fill}, Opacity={fill_opacity}, Text={repr(txt)}")
                        
        print(f"  Summary: Text in {len(text_samples)}/5 pages. Total drawings in 5 pages: {drawing_count}. Highlights found: {highlights_found}")
        doc.close()
    except Exception as e:
        print(f"  Error processing {pdf_file}: {e}")
