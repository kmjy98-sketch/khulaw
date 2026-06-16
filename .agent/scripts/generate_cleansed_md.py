import fitz
import sys
import io
import re

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

def clean_ocr_noise(text):
    # Remove running headers/footers
    text = re.sub(r'저13편\s*통치구조\s*I\s*\d+', '', text)
    text = re.sub(r'\d+\s*I\s*UNION\s*변호사시험\s*[활뿔][醒훤램]+', '', text)
    text = re.sub(r'선택형\s*기출문제집\s*1\.\s*기출편\s*•\s*[醒훤램]+', '', text)
    text = re.sub(r'제\s*3\s*편\s*-\s*통\s*지\s*구\s*조', '', text)
    text = re.sub(r'--- PAGE_(?:START|END) \d+ ---', '', text)
    return text.strip()

def process_pdf(pdf_path, ocr_rules):
    doc = fitz.open(pdf_path)
    full_text = ""
    for i in range(len(doc)):
        full_text += f"\n--- PAGE_START {i+1} ---\n" + doc[i].get_text("text") + f"\n--- PAGE_END {i+1} ---\n"
    
    for pattern, replacement in ocr_rules:
        full_text = re.sub(pattern, replacement, full_text, flags=re.IGNORECASE)
    
    matches = []
    pattern = r'(?:l\s*)?문\s*(\d+)'
    for m in re.finditer(pattern, full_text):
        num = int(m.group(1))
        matches.append((num, m.start()))
    
    matches.sort(key=lambda x: x[1])
    
    questions_data = {}
    for idx, (num, start_idx) in enumerate(matches):
        end_idx = len(full_text)
        if idx + 1 < len(matches):
            end_idx = matches[idx+1][1]
        
        q_text = full_text[start_idx:end_idx]
        questions_data[num] = q_text
        
    return questions_data

# Load questions from both files
q_03 = process_pdf(pdf_paths["03_국회_대통령"], ocr_replacements_03)
q_04 = process_pdf(pdf_paths["04_법원_헌법재판소"], ocr_replacements_04)

combined_q = {}
combined_q.update(q_03)
combined_q.update(q_04)

def parse_and_refine_question(num, raw_text):
    # Extract Year
    year_match = re.search(r'(\d{2}\s*년\s*(?:변호사시험|변시|사법시험|사시))', raw_text)
    year = year_match.group(1).replace(" ", "") if year_match else ""
    
    # Pre-clean raw text lines
    lines = [clean_ocr_noise(l) for l in raw_text.split('\n') if clean_ocr_noise(l)]
    
    # Separate Question & Options vs Explanations
    question_lines = []
    explanation_lines = []
    in_explanation = False
    
    expl_start_patterns = [r'\*\*', r'lW뀔', r'l\s*W', r'훌훨훨', r'R야I', r'l\s*R', r'lW', r'l\s*M', r'l\s*활', r'l\s*뀐']
    
    for line in lines:
        if any(re.match(pat, line) for pat in expl_start_patterns) or "정답 선지" in line or "[정답]" in line or "Explanation" in line:
            in_explanation = True
        
        if in_explanation:
            explanation_lines.append(line)
        else:
            # Skip the redundant "문 X" line or page headers
            if f"문{num}" in line.replace(" ", "") or (year and year in line.replace(" ", "")):
                continue
            question_lines.append(line)
            
    # Formulate question body and options
    # Split options on distinct markers
    body_text = " ".join(question_lines)
    # Put options on new lines
    option_markers = r'(①|②|③|④|⑤|㉠|㉡|㉢|㉣|㉤|ㄱ\.|ㄴ\.|ㄷ\.|ㄹ\.|ㅁ\.|ㄱ\s|ㄴ\s|ㄷ\s|ㄹ\s|ㅁ\s)'
    body_text = re.sub(option_markers, r'\n\1', body_text)
    body_lines = [l.strip() for l in body_text.split('\n') if l.strip()]
    
    # Process Explanation to extract:
    # 1. The correct answer number
    # 2. Brief explanation for incorrect statements
    expl_text = "\n".join(explanation_lines)
    
    # Deduce Answer
    answer_num = ""
    # Try looking for patterns like "② (X) [정답]" or "② [정답]" or "[정답] ②"
    ans_m = re.search(r'(?:[정답]\s*|[정답]\s*선지\s*|정답\s*:\s*)(①|②|③|④|⑤|ㄱ|ㄴ|ㄷ|ㄹ|ㅁ|\d)', expl_text)
    if ans_m:
        answer_num = ans_m.group(1)
    else:
        # Check for first (X) statement in explanations
        ans_m2 = re.search(r'(①|②|③|④|⑤|ㄱ|ㄴ|ㄷ|ㄹ|ㅁ)\s*\(\s*X\s*\)', expl_text)
        if ans_m2:
            answer_num = ans_m2.group(1)
        else:
            # Check for generic answers like "정답 : 2" or "** 2 **"
            ans_m3 = re.search(r'\*\*\s*([①-⑤\d])\s*\*\*', expl_text)
            if ans_m3:
                answer_num = ans_m3.group(1)
            else:
                # Look for combination answer, e.g. "① (O), L(O)" etc.
                ans_m4 = re.search(r'\[핵심\]\s*.*\s*\*+\s*([①-⑤\d])', expl_text)
                if ans_m4:
                    answer_num = ans_m4.group(1)
                else:
                    # Scan question_lines for "정답 선지"
                    for idx, ql in enumerate(question_lines):
                        if "정답 선지" in ql:
                            marker_match = re.search(option_markers, ql)
                            if marker_match:
                                answer_num = marker_match.group(1)
                                break
    
    # Normalize answer representation (convert numbers to circled numbers if needed)
    num_map = {"1": "①", "2": "②", "3": "③", "4": "④", "5": "⑤"}
    if answer_num in num_map:
        answer_num = num_map[answer_num]
    if not answer_num:
        answer_num = "확인 필요"
        
    # Extract brief corrections for incorrect (X) options
    corrections = []
    # Search for lines starting with circled numbers/letters in explanation indicating they are wrong
    # e.g., "② (X) ...", "L. (X) ..."
    expl_list = [l.strip() for l in expl_text.split('\n') if l.strip()]
    for line in expl_list:
        # Match option corrections
        match_x = re.match(r'^[-•]?\s*(?:[①-⑤]|[①-⑤]\s*\(X\)|[a-zA-Z가-힣]\s*\(X\)|[①-⑤]\s*\(O\)\s*,\s*[①-⑤]\s*\(X\))\s*(.*)', line)
        if "(X)" in line or "틀렸다" in line or "위반된다" in line or "침해한다" in line:
            # Only capture lines that explain why it is wrong
            # Extract first 1-2 sentences of the explanation
            clean_line = re.sub(r'^[-\s•①-⑤\(\)OX정답\[\]]+', '', line).strip()
            # Remove citations
            clean_line = re.sub(r'\[\[.*?\]\]|\(.*?\)', '', clean_line).strip()
            if clean_line and len(clean_line) > 10:
                sentences = re.split(r'(?<=[.!?])\s+', clean_line)
                correction_summary = sentences[0]
                if len(sentences) > 1 and len(correction_summary) < 40:
                    correction_summary += " " + sentences[1]
                # Filter out repetitive definitions or headers
                if not any(keyword in correction_summary for keyword in ["정당법 제", "헌법 제", "국회법"]):
                    corrections.append(correction_summary)
                    
    # Format the markdown response for this question
    md = f"##### 【{year} 문{num}】 (정답: **{answer_num}**)\n"
    
    # Append question text
    for line in body_lines:
        # Highlight the correct answer option if matched
        if answer_num and answer_num in line and len(line) < 300:
            md += f"**{line} (정답)**\n"
        else:
            md += f"{line}\n"
            
    # Append corrections instead of full explanation
    if corrections:
        md += "\n* **오답 바로잡기**:\n"
        for corr in list(set(corrections))[:2]: # limit to top 2 main corrections
            md += f"  - {corr}\n"
    md += "\n---\n\n"
    
    return md

# Compile final cleansed markdown
final_markdown = "# 유니온 헌법 기출 제3편 통치구조 문제 초간결 정제본\n\n"
for num in target_nums:
    if num in combined_q:
        final_markdown += parse_and_refine_question(num, combined_q[num])
    else:
        final_markdown += f"##### 【문{num}】 (미확인)\nPDF 소스에서 문항을 찾을 수 없습니다.\n\n---\n\n"

# Save to C:\Users\111\.gemini\antigravity\scratch\final_questions.md
out_path = r"C:\Users\111\.gemini\antigravity\scratch\final_questions.md"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(final_markdown)

print("Cleansed markdown generated successfully!")
