import fitz
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

pdf_dir = vp("리퀴드텍스트 참조")
output_dir = r"C:\Users\111\.gemini\antigravity\scratch\extracted_highlights"

os.makedirs(output_dir, exist_ok=True)

pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]

print(f"Target directory: {pdf_dir}")
print(f"Output directory: {output_dir}")
print(f"Found {len(pdf_files)} PDF files to process.")

for pdf_file in pdf_files:
    pdf_path = os.path.join(pdf_dir, pdf_file)
    output_md_path = os.path.join(output_dir, f"{os.path.splitext(pdf_file)[0]}_highlights.md")
    
    print(f"\nProcessing: {pdf_file} ...")
    try:
        doc = fitz.open(pdf_path)
        markdown_lines = []
        markdown_lines.append(f"# {pdf_file} 형광펜 발췌\n")
        
        total_highlights = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            drawings = page.get_drawings()
            if not drawings:
                continue
                
            page_highlights = []
            for draw in drawings:
                fill_opacity = draw.get('fill_opacity')
                if fill_opacity is None:
                    fill_opacity = 1.0
                
                # LiquidText highlight opacity condition
                if 0.45 <= fill_opacity <= 0.55:
                    rect = draw.get('rect')
                    if rect:
                        text = page.get_text("text", clip=rect).strip()
                        if text:
                            page_highlights.append({
                                'rect': rect,
                                'text': text
                            })
            
            if page_highlights:
                page_highlights.sort(key=lambda x: (round(x['rect'].y0, 1), round(x['rect'].x0, 1)))
                
                markdown_lines.append(f"## Page {page_num + 1}\n")
                
                prev_text = ""
                for item in page_highlights:
                    curr_text = item['text']
                    if curr_text == prev_text:
                        continue
                    
                    cleaned_text = " ".join(curr_text.split())
                    markdown_lines.append(f"- {cleaned_text}")
                    prev_text = curr_text
                    total_highlights += 1
                
                markdown_lines.append("")
                
        if total_highlights > 0:
            with open(output_md_path, "w", encoding="utf-8") as f:
                f.write("\n".join(markdown_lines))
            print(f"  -> Extracted {total_highlights} highlights to {output_md_path}")
        else:
            print("  -> No highlights found.")
            
        doc.close()
    except Exception as e:
        print(f"  -> Error processing {pdf_file}: {e}")

print("\nAll processing completed.")
