import fitz
import os

folder_path = r"H:\내 드라이브\리퀴드텍스트 참조"
pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]

for pdf_file in pdf_files:
    pdf_path = os.path.join(folder_path, pdf_file)
    try:
        doc = fitz.open(pdf_path)
        has_text_pages = 0
        highlight_candidates = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:
                has_text_pages += 1
                
            drawings = page.get_drawings()
            for draw_idx, draw in enumerate(drawings):
                fill = draw.get('fill')
                fill_opacity = draw.get('fill_opacity')
                if fill_opacity is None:
                    fill_opacity = 1.0
                stroke_opacity = draw.get('stroke_opacity')
                if stroke_opacity is None:
                    stroke_opacity = 1.0
                
                is_candidate = False
                if fill:
                    r, g, b = fill
                    # Yellow highlight: R > 0.8, G > 0.8, B < 0.6
                    if r > 0.8 and g > 0.8 and b < 0.6:
                        is_candidate = True
                    # Green: R < 0.6, G > 0.8, B < 0.6
                    elif r < 0.6 and g > 0.8 and b < 0.6:
                        is_candidate = True
                    # Cyan/Blue: R < 0.6 and G > 0.6 and B > 0.8
                    elif r < 0.6 and g > 0.6 and b > 0.8:
                        is_candidate = True
                    # Magenta/Pink: R > 0.8 and G < 0.6 and B > 0.8
                    elif r > 0.8 and g < 0.6 and b > 0.8:
                        is_candidate = True
                        
                if fill_opacity < 0.95 or stroke_opacity < 0.95:
                    is_candidate = True
                    
                if is_candidate:
                    highlight_candidates.append({
                        'page': page_num + 1,
                        'rect': draw.get('rect'),
                        'fill': fill,
                        'fill_opacity': fill_opacity,
                        'stroke_opacity': stroke_opacity,
                        'text': page.get_text("text", clip=draw.get('rect')).strip()
                    })
                    
        print(f"File: {pdf_file}")
        print(f"  Pages with text: {has_text_pages} / {len(doc)}")
        print(f"  Highlight candidates found: {len(highlight_candidates)}")
        if highlight_candidates:
            print("  Sample candidates (up to 5):")
            for c in highlight_candidates[:5]:
                print(f"    Page {c['page']}: Rect={c['rect']}, Fill={c['fill']}, Opacity={c['fill_opacity']}, Text={repr(c['text'])}")
        doc.close()
    except Exception as e:
        print(f"Error processing {pdf_file}: {e}")
