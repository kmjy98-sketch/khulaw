import os
import sys
import subprocess
import re
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

# Set console encoding to UTF-8
os.environ["PYTHONIOENCODING"] = "utf-8"

dir_path = Path(vp("작업용"))
ocr_out_dir = Path(vp("outputs", "01_ocr"))
wiki_out_dir = Path(vp("outputs", "02_wiki"))

os.makedirs(ocr_out_dir, exist_ok=True)
os.makedirs(wiki_out_dir, exist_ok=True)

remaining_targets = [
    {
        "pdf": "2026 논점 민사소송법 - 변호사 시험 & 각종 국가고시 대비,_3c_r6_d2.pdf",
        "prefix": "송영곤_민사소송법_26",
        "subject": "민사",
        "author": "송영곤",
        "book": "논점 민사소송법 2026"
    },
    {
        "pdf": "2026 민사법 사례연습 1 - 진도별 요약형 - 제2판_3c_r6_d2 (1).pdf",
        "prefix": "송영곤_민사사례연습1_26",
        "subject": "민사",
        "author": "송영곤",
        "book": "민사법 사례연습 1"
    },
    {
        "pdf": "[5+1] 2027 해커스변호사 변호사시험 기출문제집 헌법 사례형 - 최신개정판ㅣ변호사시험 등 각종 국가고_3c_r6_d2.pdf",
        "prefix": "해커스_헌법사례형_27",
        "subject": "공법",
        "author": "해커스",
        "book": "해커스 헌법 사례형 2027"
    },
    {
        "pdf": "compact형법총론OX_26.pdf",
        "prefix": "이인규_형총OX_26",
        "subject": "형사",
        "author": "이인규",
        "book": "COMPACT 형법총론 OX 2026"
    },
    {
        "pdf": "김기용_형법총론_교안_26.pdf",
        "prefix": "김기용_형총교안_26",
        "subject": "형사",
        "author": "김기용",
        "book": "형법총론 교안 2026"
    },
    {
        "pdf": "논점민법강의_재산법_26.pdf",
        "prefix": "송영곤_논점민법재산법_26",
        "subject": "민사",
        "author": "송영곤",
        "book": "논점민법강의 재산법 2026"
    },
    {
        "pdf": "송영곤_신민사법선택형연습1_민법총칙_26.pdf",
        "prefix": "송영곤_선택형연습_민총_26",
        "subject": "민사",
        "author": "송영곤",
        "book": "신민사법 선택형연습 1 민법총칙"
    },
    {
        "pdf": "송영곤_신민사법선택형연습1_물권법_26.pdf",
        "prefix": "송영곤_선택형연습_물권_26",
        "subject": "민사",
        "author": "송영곤",
        "book": "신민사법 선택형연습 1 물권법"
    },
    {
        "pdf": "송영곤_신민사법선택형연습1_채권법1_26.pdf",
        "prefix": "송영곤_선택형연습_채권1_26",
        "subject": "민사",
        "author": "송영곤",
        "book": "신민사법 선택형연습 1 채권법 1"
    },
    {
        "pdf": "송영곤_신민사법선택형연습1_채권법2_26.pdf",
        "prefix": "송영곤_선택형연습_채권2_26",
        "subject": "민사",
        "author": "송영곤",
        "book": "신민사법 선택형연습 1 채권법 2"
    },
    {
        "pdf": "유니온 헌법 기출편(2027 대비).pdf",
        "prefix": "유니온_헌법기출_27",
        "subject": "공법",
        "author": "유니온",
        "book": "유니온 헌법 기출편 2027"
    },
    {
        "pdf": "작은변사기형법_25.pdf",
        "prefix": "신호진_작은변사기형법_25",
        "subject": "형사",
        "author": "신호진",
        "book": "작은 변호사시험 사례 기출 형법 2025"
    }
]

print("Starting remaining PDFs processing pipeline (subprocess mode)...")
print("-" * 60)

for t in remaining_targets:
    pdf_path = dir_path / t["pdf"]
    if not pdf_path.exists():
        print(f"[MISSING] {t['pdf']} does not exist in {dir_path}")
        continue
        
    print(f"\n==================== PROCESSING: {t['book']} ====================")
    
    # 1. Split PDF
    print(f"[STEP 1/3] Splitting {t['pdf']} into 100-page chunks...")
    split_script = vp("pdf_split_100p.py")
    try:
        subprocess.run(
            [sys.executable, split_script, str(pdf_path)],
            check=True
        )
        print("  [SUCCESS] Split completed.")
    except Exception as e:
        print(f"  [ERROR] Split failed: {e}")
        continue
        
    # 2. Extract Text (Corrected file name to code_pdf_extract_2026-04-30.py)
    print(f"[STEP 2/3] Extracting text to {ocr_out_dir}...")
    extract_script = vp(".agent", "scripts", "code_pdf_extract_2026-04-30.py")
    try:
        cmd = [
            sys.executable, extract_script,
            "--pdf", str(pdf_path),
            "--out", str(ocr_out_dir),
            "--prefix", t["prefix"],
            "--subject", t["subject"],
            "--author", t["author"],
            "--book", t["book"],
            "--chunk-size", "30"
        ]
        subprocess.run(cmd, check=True)
        print("  [SUCCESS] Text extraction completed.")
    except Exception as e:
        print(f"  [ERROR] Text extraction failed: {e}")
        continue
        
    # 3. Transform to Wiki
    print(f"[STEP 3/3] Structuring to wiki markdown in {wiki_out_dir}...")
    try:
        # Find all generated chunks for this prefix
        generated_chunks = [f for f in os.listdir(ocr_out_dir) if f.startswith(t["prefix"]) and f.endswith(".md")]
        print(f"  Found {len(generated_chunks)} chunk files to convert.")
        
        sys.path.append(vp(".agent", "scripts"))
        import wiki_transformer
        
        count = 0
        for f in generated_chunks:
            in_file = ocr_out_dir / f
            out_file = wiki_out_dir / f
            
            with open(in_file, "r", encoding="utf-8") as fh:
                raw_content = fh.read()
                
            transformed = wiki_transformer.transform_to_wiki(raw_content, f)
            
            with open(out_file, "w", encoding="utf-8") as fh:
                fh.write(transformed)
            count += 1
        print(f"  [SUCCESS] Wiki files written: {count}")
    except Exception as e:
        print(f"  [ERROR] Wiki transformation failed: {e}")

print("\n" + "-" * 60)
print("Pipeline finished successfully for remaining target PDFs.")
