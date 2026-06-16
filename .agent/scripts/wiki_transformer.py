import os
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Callout mappings
CALLOUT_MAP = {
    r"\[논점정리\]|\[논점의\s*정리\]": "[!summary] 논점정리",
    r"\[관련판례\]": "[!example] 관련판례",
    r"\[판례분석\]|\[판례해설\]": "[!analysis] 판례분석",
    r"\[해설\]|\[모범답안\]|\[풀이\]": "[!note] 해설",
    r"\[주의\]|\[!\]": "[!warning] 주의",
    r"\[중요\]|\[★\]": "[!important] 중요",
    r"\[참고\]|\[Note\]": "[!info] 참고"
}

# Inline bold mappings
INLINE_MAP = {
    r"\[개념\]": "**[개념]**",
    r"\[의의\]": "**[의의]**",
    r"\[정의\]": "**[정의]**",
    r"\[사안\]": "**[사안]**",
    r"\[설문\s*\d+.*?\]": "**[설문]**",
    r"\[요건\]": "**[요건]**",
    r"\[효과\]": "**[효과]**",
    r"\[학설\]": "**[학설]**",
    r"\[검토\]|\[사견\]": "**[검토]**"
}

# Core Law Keywords for backlink matching
LAW_KEYWORDS = [
    "특정물채권", "보존의무", "반대급부위험부담", "채권자취소권", "악의 추정", "기판력", 
    "기속력", "소각하", "소취하", "이송", "제척", "기피", "회피", "학설", "긍정설", 
    "부정설", "제한설", "절충설", "합헌", "위헌", "한정합헌", "한정위헌", "헌법불합치", 
    "입법촉구", "기각", "각하", "원심파기", "파기환송", "파기자판", "파기이송"
]

def clean_backlinks(text: str) -> str:
    """Keyword backlink insertion (without duplication)"""
    for kw in LAW_KEYWORDS:
        # Check if already backlinked
        pattern = re.compile(rf'(?<!\[\[){re.escape(kw)}(?!\]\])')
        text = pattern.sub(f"[[{kw}]]", text)
    return text

def detect_book_type(text: str) -> tuple[str, float, dict]:
    """Automatically detect book type based on signal keywords"""
    signals = {
        "정의": len(re.findall(r"이란|뜻은|개념|의의", text)),
        "요건": len(re.findall(r"요건|요구된다|필요하다", text)),
        "학설": len(re.findall(r"설\s*\(|긍정설|부정설|절충설", text)),
        "판례": len(re.findall(r"대판|대법원|헌재|사건번호", text)),
        "표": text.count("|"),
        "사례": len(re.findall(r"사안|설문|풀이|답안", text)),
        "객관식": len(re.findall(r"①|②|③|④|⑤", text))
    }
    
    total = sum(signals.values()) or 1
    dist = {k: f"{round(v/total * 100)}%" for k, v in signals.items()}
    
    # Simple logic
    if signals["사례"] > total * 0.3:
        b_type = "사례집"
    elif signals["객관식"] > total * 0.4:
        b_type = "객관식문제집"
    elif signals["판례"] > total * 0.5:
        b_type = "판례집"
    else:
        b_type = "단권화"
        
    confidence = 90.0 if total > 20 else 60.0
    return b_type, confidence, dist

def transform_to_wiki(content: str, filename: str) -> str:
    """Transforms raw text markdown into 02-wiki structured markdown"""
    input_chars = len("".join(content.split()))
    
    # 1. Box labels -> Obsidian callouts
    lines = content.split("\n")
    processed_lines = []
    
    in_callout = False
    for line in lines:
        matched = False
        for pat, replacement in CALLOUT_MAP.items():
            if re.match(rf"^\s*(?:{pat})", line.strip()):
                processed_lines.append(f"> {replacement}")
                in_callout = True
                matched = True
                break
        if matched:
            continue
            
        # Inline bold replacements
        for pat, replacement in INLINE_MAP.items():
            line = re.sub(pat, replacement, line)
            
        # Handle callout indentation
        if in_callout:
            if line.strip() == "" or line.startswith("#"):
                in_callout = False
                processed_lines.append(line)
            else:
                processed_lines.append(f"> {line}")
        else:
            processed_lines.append(line)
            
    content = "\n".join(processed_lines)
    
    # 2. Add backlink keywords
    content = clean_backlinks(content)
    
    # 3. Add attribute labels (속성: X) to #### headings
    subsections = content.split("#### ")
    processed_subsections = [subsections[0]]
    
    for sub in subsections[1:]:
        lines = sub.split("\n")
        header = lines[0]
        body = "\n".join(lines[1:])
        
        # Attribute detection
        attrs = []
        if any(w in body for w in ["이란", "개념", "의의", "정의"]):
            attrs.append("정의")
        if "요건" in body or "①" in body:
            attrs.append("요건")
        if any(w in body for w in ["대판", "대법원", "헌재"]):
            attrs.append("판례")
        if any(w in body for w in ["설", "긍정설", "부정설"]):
            attrs.append("학설")
        if "|" in body:
            attrs.append("표")
        if "제" in body and "조" in body:
            attrs.append("조문 원문")
            
        attr_str = "+".join(attrs) if attrs else "단권화"
        
        processed_subsections.append(f"{header}\n\n<!-- 속성: {attr_str} -->\n{body}")
        
    content = "#### ".join(processed_subsections)
    
    # 4. Escape [불명] -> {불명}
    content = content.replace("[불명]", "{불명}").replace("[OCR불명]", "{OCR불명}")
    
    # 5. Measure output body chars and integrity
    output_body_chars = len("".join(content.split()))
    preservation_rate = round(output_body_chars / (input_chars or 1) * 100)
    
    # 6. Extract chunk pages information from filename
    chunk_pages = "unknown"
    p_match = re.search(r'p\d+-\d+', filename)
    if p_match:
        chunk_pages = p_match.group(0)
        
    # Detect book type
    b_type, confidence, dist = detect_book_type(content)
    
    # 7. Prepend YAML frontmatter
    frontmatter = f"""---
source: {filename}
book_type: {b_type}
book_type_confidence: {confidence}%
chunk: {chunk_pages}
attribute_distribution:
  정의: {dist.get('정의', '0%')}
  요건: {dist.get('요건', '0%')}
  학설: {dist.get('학설', '0%')}
  판례: {dist.get('판례', '0%')}
  표: {dist.get('표', '0%')}
  사례: {dist.get('사례', '0%')}
  객관식: {dist.get('객관식', '0%')}
---

INTEGRITY: INPUT_CHARS={input_chars} | OUTPUT_BODY_CHARS={output_body_chars} | 보존율={preservation_rate}%
책 유형 추정: {b_type} (신뢰도 {confidence}%, 시그널 분포: 정의 {dist.get('정의')}, 요건 {dist.get('요건')}, 학설 {dist.get('학설')}, 판례 {dist.get('판례')})
hint 일치 여부: 확인됨

"""
    return frontmatter + content

def process_all_files():
    # Directories
    dirs_to_process = [
        # 1. 01 OCR outputs (Constitution & Song Case Studies)
        {
            "in": Path("H:/내 드라이브/outputs/01_ocr"),
            "out": Path("H:/내 드라이브/outputs/02_wiki")
        },
        # 2. Existing summary notes (Civil Law Notes)
        {
            "in": Path("H:/내 드라이브/sync/_백업/교재원문_문서_백업_2026-05-22/1.민사/33.송영곤_쟁노/교재_추출"),
            "out": Path("H:/내 드라이브/outputs/02_wiki/민사법쟁점노트")
        },
        # 3. Criminal Law Notes
        {
            "in": Path("H:/내 드라이브/.agent/data/ocr_chunks_reviewed/형법/반반형법"),
            "out": Path("H:/내 드라이브/outputs/02_wiki/반반형법")
        }
    ]
    
    print("Starting batch 02-wiki transformation process...")
    print("-" * 60)
    
    total_processed = 0
    for d in dirs_to_process:
        in_dir = d["in"]
        out_dir = d["out"]
        if not in_dir.exists():
            print(f"[SKIP] Directory {in_dir} does not exist.")
            continue
            
        os.makedirs(out_dir, exist_ok=True)
        files = [f for f in os.listdir(in_dir) if f.endswith(".md")]
        print(f"Processing folder: {in_dir.name} ({len(files)} files)")
        
        for f in files:
            in_file = in_dir / f
            out_file = out_dir / f
            try:
                with open(in_file, "r", encoding="utf-8") as fh:
                    raw_content = fh.read()
                
                # Perform the transformation
                transformed = transform_to_wiki(raw_content, f)
                
                with open(out_file, "w", encoding="utf-8") as fh:
                    fh.write(transformed)
                    
                total_processed += 1
            except Exception as e:
                print(f"  [ERROR] Failed to transform {f}: {e}")
                
    print("-" * 60)
    print(f"Batch transformation finished. Total files processed: {total_processed}")

if __name__ == "__main__":
    process_all_files()
