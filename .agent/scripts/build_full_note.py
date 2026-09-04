import os
import pypdf
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')

pdf_files = {
    "핵정_헌재": vp("3.공법", "_분할", "핵심정리300_01_헌법재판.pdf"),
    "핵정_총론": vp("3.공법", "_분할", "핵심정리300_03_기본권_나머지_헌법총론.pdf"),
    "핵정_통치": vp("3.공법", "_분할", "핵심정리300_04_통치구조.pdf"),
    "유니온_통치": vp("3.공법", "_분할", "유니온헌법기출편_03_통치구조_국회_대통령.pdf"),
    "유니온_헌재": vp("3.공법", "_분할", "유니온헌법기출편_04_법원_헌법재판소.pdf"),
    "해커스_헌재": vp("3.공법", "_분할", "2027해커스헌법사례형_01_헌법재판.pdf"),
    "해커스_통치": vp("3.공법", "_분할", "2027해커스헌법사례형_03_헌법총론_통치구조.pdf")
}

hanja_map = {
    "甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무", "己": "기", "庚": "경", "辛": "신", "壬": "임", "癸": "계",
    "條": "조", "但": "단", "項": "항", "號": "호", "法": "법", "憲": "헌", "判": "판", "決": "결", "例": "례",
    "審": "심", "所": "소", "院": "원", "檢": "검", "警": "경", "訴": "소", "被": "피", "告": "고", "證": "증",
    "人": "인", "사": "사", "건": "건"
}

foreign_map = {
    "in dubio pro legislatore": "의심스러울 때는 합헌으로",
    "in dubio pro reo": "의심스러울 때는 피고인의 이익으로",
    "lex posterior derogat legi priori": "신법우위의 원칙",
    "lex specialis derogat legi generali": "특별법우위의 원칙"
}

def clean_text(text):
    for eng, kor in foreign_map.items():
        text = re.sub(eng, kor, text, flags=re.IGNORECASE)
    
    text = re.sub(r'\([\u4e00-\u9fff]+\)', '', text)
    text = re.sub(r'（[\u4e00-\u9fff]+）', '', text)
    
    for hj, hg in hanja_map.items():
        text = text.replace(hj, hg)
        
    text = text.replace("()", "").replace("（）", "")
    
    # Using raw replacement correctly
    text = re.sub(r'제([1-9][0-9]+조(?:의\s*[0-9]+)?)', r'[[§\1]]', text)
    text = text.replace("조]]", "]]")
    
    text = re.sub(r'(헌재\s+[0-9]{4}\.\s*[0-9]{1,2}\.\s*[0-9]{1,2}\.?\s*[0-9]{2,4}헌[가나다라마바사아자차카타파하][0-9]+)', r'[[\1]]', text)
    text = re.sub(r'(대판\s+[0-9]{4}\.\s*[0-9]{1,2}\.\s*[0-9]{1,2}\.?\s*[0-9]{2,4}다[0-9]+)', r'[[\1]]', text)
    
    return text

def extract_pdf_range(path, start_page, end_page):
    if not os.path.exists(path):
        return f"[Error: File {path} not found]"
    text_content = []
    try:
        with open(path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            total_p = len(reader.pages)
            s_idx = max(0, start_page - 1)
            e_idx = min(total_p, end_page)
            for idx in range(s_idx, e_idx):
                p_text = reader.pages[idx].extract_text()
                lines = p_text.split('\n')
                cleaned_lines = [line.strip() for line in lines if line.strip()]
                text_content.append("\n".join(cleaned_lines))
        return clean_text("\n\n".join(text_content))
    except Exception as e:
        import traceback
        return f"[Error extracting PDF: {e} | {traceback.format_exc()}]"

def build_note():
    print("Process Start: Compiling full note to 헌법_안티그래비티.md...")
    
    draft_path = "C:/Users/111/.gemini/antigravity/scratch/이진헌법1_기말_종합노트_초안.md"
    if os.path.exists(draft_path):
        with open(draft_path, 'r', encoding='utf-8') as f:
            full_note = f.read()
    else:
        full_note = "# 이진교수님 헌법 1 기말 종합노트\n\n"

    # Rename title inside markdown
    full_note = full_note.replace("이진교수님 헌법 1 기말 종합노트 (초안 백업본)", "이진교수님 헌법 1 기말 종합노트 (헌법_안티그래비티)")

    # Extractions
    print("Step 1: Extracting Sec 1...")
    sec1_text = extract_pdf_range(pdf_files["핵정_총론"], 60, 84)
    
    print("Step 2: Extracting Sec 2 Core...")
    sec2_text_core = extract_pdf_range(pdf_files["핵정_헌재"], 1, 45)
    
    print("Step 3: Extracting Sec 2 Case...")
    sec2_text_case = extract_pdf_range(pdf_files["해커스_헌재"], 1, 40)
    
    print("Step 4: Extracting Sec 3 Core...")
    sec3_text_core = extract_pdf_range(pdf_files["핵정_통치"], 1, 50)

    print("Step 5: Extracting Sec 3 Union...")
    sec3_text_union = extract_pdf_range(pdf_files["유니온_통치"], 1, 50)
    
    # Precise replacements using existing draft sections
    target_sec1 = "### 1-5. [[과잉금지원칙]] (비례원칙)"
    if target_sec1 in full_note:
        replacement = f"{target_sec1}\n\n#### 1-5-2. 핵심정리 300 법치주의 원문 발췌\n\n{sec1_text}"
        full_note = full_note.replace(target_sec1, replacement)
        print("Replacement 1 complete")
        
    target_sec2 = "### 2-3. 가처분"
    if target_sec2 in full_note:
        replacement = f"{target_sec2}\n\n#### 2-3-2. 핵심정리 300 헌법재판 원문 발췌\n\n{sec2_text_core}\n\n#### 2-3-3. 해커스 사례형 헌법재판 사례 문제 및 풀이 원문\n\n{sec2_text_case}"
        full_note = full_note.replace(target_sec2, replacement)
        print("Replacement 2 complete")

    target_sec3 = "## 3. 선택형 (중간 이후 전 단원)"
    if target_sec3 in full_note:
        replacement = f"{target_sec3}\n\n### 3-1. 핵심정리 300 통치구조 기본 이론 원문\n\n{sec3_text_core}\n\n### 3-2. 유니온 기출 통치구조(국회·대통령) 문제 및 해설 원문\n\n{sec3_text_union}"
        full_note = full_note.replace(target_sec3, replacement)
        print("Replacement 3 complete")
        
    out_path = vp("sync", "1-1_기말", "헌법_안티그래비티.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as out_f:
        out_f.write(full_note)
    print("Process Finished Successfully!")
    
if __name__ == "__main__":
    build_note()
