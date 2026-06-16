import fitz
import sys
import io
import re

# Enforce UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

pdf_paths = {
    "03_국회_대통령": r"H:\내 드라이브\3.공법\_분할\유니온헌법기출편_03_통치구조_국회_대통령.pdf",
    "04_법원_헌법재판소": r"H:\내 드라이브\3.공법\_분할\유니온헌법기출편_04_법원_헌법재판소.pdf"
}

target_nums = [
    1, 5, 6, 7, 8, 12, 13, 14, 15, 16, 17, 21, 24, 26, 27, 28, 32, 33, 39, 44, 45, 49, 51, 52, 58, 59, 61, 66, 67, 68,
    77, 78, 79, 80, 83, 84, 85, 86, 87, 88, 90, 91, 98, 99, 100, 107, 108, 109, 110, 111, 112, 113, 114, 130, 133, 134,
    140, 141, 142, 150, 151, 152, 155
]

# Replacement rules for OCR corrupted question markers
ocr_replacements_03 = [
    (r"l\s*푼\s*5", "l 문 5"),
    (r"l\s*문\s*i\b", "l 문 6"),
    (r"l\s*문\s*T\b", "l 문 7"),
    (r"l\s*문\s*용\b", "l 문 8")
]

ocr_replacements_04 = [
    (r"l\s*룹\s*ìì", "l 문 77"),
    (r"짧\s*CI\s*\.\.\s*An\s*힌\s*:\-\s*I\s*‘1\'U\s*\?fl념\s*벼룰Å~ÅI\s*혁", "l 문 140")
]

def clean_text_formatting(text):
    # Normalize whitespaces and remove unnecessary lines or headers
    text = re.sub(r'저13편\s*통치구조\s*I\s*\d+', '', text)
    text = re.sub(r'\d+\s*I\s*UNION\s*변호사시험\s*[활뿔][醒훤램]+', '', text)
    text = re.sub(r'선택형\s*기출문제집\s*1\.\s*기출편\s*•\s*[醒훤램]+', '', text)
    text = re.sub(r'제\s*3\s*편\s*-\s*통\s*지\s*구\s*조', '', text)
    # Simplify multiple blank lines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def format_citation(text):
    # Convert citation formats like (헌재 2022.07.21. 2018헌바164) to [[헌재 2022.7.21, 2018헌바164]]
    # or (대판 2010.12.09. 2010도7410) to [[대판 2010.12.9, 2010도7410]]
    def repl(match):
        court = match.group(1)
        date_str = match.group(2)
        case_no = match.group(3)
        # Normalize date (e.g. 2022.07.01 -> 2022.7.1)
        parts = date_str.split('.')
        parts = [str(int(p)) for p in parts if p.strip()]
        normalized_date = ".".join(parts)
        return f"[[{court} {normalized_date}, {case_no}]]"

    # Match (헌재 YYYY.MM.DD. CaseNo) or (대판 YYYY.MM.DD. CaseNo)
    pattern = r'\(([헌재대판]+)\s+(\d{4}\.\d{2}\.\d{2}\.?)\s+([^)]+)\)'
    text = re.sub(pattern, repl, text)
    return text

def process_pdf(pdf_key, pdf_path, ocr_rules):
    print(f"Processing {pdf_key}...")
    doc = fitz.open(pdf_path)
    full_text = ""
    for i in range(len(doc)):
        full_text += f"\n--- PAGE_START {i+1} ---\n" + doc[i].get_text("text") + f"\n--- PAGE_END {i+1} ---\n"
    
    # Apply OCR correction rules
    for pattern, replacement in ocr_rules:
        full_text = re.sub(pattern, replacement, full_text, flags=re.IGNORECASE)
    
    # Find all question starting points
    # Standard format: l 문 X or 문 X or 홉 문 X, etc.
    # We will locate "l 문 [0-9]+" or "문 [0-9]+" or "문[0-9]+"
    matches = []
    pattern = r'(?:l\s*)?문\s*(\d+)'
    for m in re.finditer(pattern, full_text):
        num = int(m.group(1))
        matches.append((num, m.start(), m.group(0)))
    
    # Sort matches by start index
    matches.sort(key=lambda x: x[1])
    
    # Slice text for each question
    questions_data = {}
    for idx, (num, start_idx, matched_str) in enumerate(matches):
        end_idx = len(full_text)
        if idx + 1 < len(matches):
            end_idx = matches[idx+1][1]
        
        q_text = full_text[start_idx:end_idx]
        questions_data[num] = q_text
        
    return questions_data

# Process both PDFs
q_data_03 = process_pdf("03_국회_대통령", pdf_paths["03_국회_대통령"], ocr_replacements_03)
q_data_04 = process_pdf("04_법원_헌법재판소", pdf_paths["04_법원_헌법재판소"], ocr_replacements_04)

# Combine questions data
combined_questions = {}
combined_questions.update(q_data_03)
combined_questions.update(q_data_04)

print(f"Total questions parsed: {len(combined_questions)}")

# Now, format target questions
final_markdown = "# 유니온 헌법 기출 제3편 통치구조 문제 정제본\n\n"

for num in target_nums:
    if num not in combined_questions:
        print(f"Warning: 문{num} was not found in either PDF.")
        final_markdown += f"##### 【문 {num}】 (미확인)\n\nPDF 소스에서 문항 텍스트를 찾을 수 없습니다.\n\n---\n\n"
        continue
        
    raw_q_text = combined_questions[num]
    
    # Split raw_q_text into lines and extract components
    lines = [line.strip() for line in raw_q_text.split('\n') if line.strip()]
    
    # Simple heuristic to extract:
    # 1. Title/Header (usually the first few lines including year)
    # 2. Question body & options
    # 3. Answer & Explanation
    
    title_parts = []
    question_body = []
    explanation = []
    
    in_explanation = False
    
    # Identify Year (e.g. 22 년 변호사시험, 22년 변시)
    year_match = re.search(r'(\d{2}\s*년\s*(?:변호사시험|변시|사법시험|사시))', raw_q_text)
    year = year_match.group(1).replace(" ", "") if year_match else ""
    
    # We will build clean formatting
    title_line = f"##### 【{year} 문{num}】"
    
    # Let's separate question and explanation.
    # Explanation usually starts with double asterisks or lW뀔I, 훌훨훨, R야I 등
    expl_start_patterns = [r'\*\*', r'lW뀔', r'l\s*W', r'훌훨훨', r'R야I', r'l\s*R', r'lW', r'l\s*M']
    
    for line in lines:
        if any(re.match(pat, line) for pat in expl_start_patterns) or "정답 선지" in line or "[정답]" in line or "Explanation" in line:
            in_explanation = True
        
        if in_explanation:
            explanation.append(line)
        else:
            if f"문{num}" in line or f"문 {num}" in line or (year and year in line.replace(" ", "")):
                # Skip the title-like line in the question body
                continue
            question_body.append(line)
            
    # Format options and body
    body_formatted = ""
    for line in question_body:
        # Match option markers like ①, ②, ③, ④, ⑤, ㄱ, ㄴ, ㄷ, ㄹ, ㅁ
        if re.match(r'^(?:①|②|③|④|⑤|㉠|㉡|㉢|㉣|㉤|ㄱ|ㄴ|ㄷ|ㄹ|ㅁ|\([0-9]+\))\s*', line):
            body_formatted += f"\n{line}"
        else:
            if body_formatted:
                body_formatted += f" {line}"
            else:
                body_formatted += line
                
    # Format explanation and extract answer
    answer = "확인 필요"
    expl_formatted = ""
    
    # Try to find answer
    # Answers in explanation are often marked like: ** 1 ** or [정답] or (2) [정답] or (정답 선지)
    ans_match = re.search(r'\[정답\]\s*(?:지방자치단체의|①|②|③|④|⑤|[\d]+)', "\n".join(explanation))
    if ans_match:
        answer = ans_match.group(0)
    else:
        # Check for (X) in options explanation
        for line in explanation:
            m = re.search(r'(?:①|②|③|④|⑤|\d+)\s*\((?:X|정답)\)', line)
            if m:
                answer = m.group(0)
                break
                
    # Format explanation lines
    for line in explanation:
        line = format_citation(line)
        if re.match(r'^(?:①|②|③|④|⑤|ㄱ|ㄴ|ㄷ|ㄹ|ㅁ|\(\d+\))\s*', line):
            expl_formatted += f"\n- {line}"
        else:
            if expl_formatted:
                expl_formatted += f" {line}"
            else:
                expl_formatted += line
                
    # Clean up
    body_formatted = clean_text_formatting(body_formatted)
    expl_formatted = clean_text_formatting(expl_formatted)
    
    final_markdown += f"{title_line}\n"
    final_markdown += f"{body_formatted}\n\n"
    final_markdown += f"**정답**: {answer}\n\n"
    final_markdown += f"**해설**:\n{expl_formatted}\n\n"
    final_markdown += "---\n\n"

# Write final markdown to C:\Users\111\.gemini\antigravity\scratch\final_questions.md
out_path = r"C:\Users\111\.gemini\antigravity\scratch\final_questions.md"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(final_markdown)

print(f"Successfully wrote final markdown to {out_path}")
