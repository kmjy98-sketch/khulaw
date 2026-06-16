import os
import glob
import pypdf

def extract_pdf_to_txt(pdf_path, txt_path):
    print(f"Extracting {pdf_path} -> {txt_path}")
    try:
        reader = pypdf.PdfReader(pdf_path)
        text_content = []
        for i, page in enumerate(reader.pages):
            text_content.append(f"--- Page {i+1} ---")
            text_content.append(page.extract_text() or "")
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(text_content))
    except Exception as e:
        print(f"Failed to extract {pdf_path}: {e}")

def main():
    pdf_dir = "H:/내 드라이브/4.선택법/10.법조윤리/기출"
    out_dir = "C:/Users/111/.gemini/antigravity/scratch"
    os.makedirs(out_dir, exist_ok=True)
    
    pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    for pdf_path in pdf_files:
        basename = os.path.splitext(os.path.basename(pdf_path))[0]
        txt_path = os.path.join(out_dir, f"{basename}.txt")
        extract_pdf_to_txt(pdf_path, txt_path)

if __name__ == "__main__":
    main()
