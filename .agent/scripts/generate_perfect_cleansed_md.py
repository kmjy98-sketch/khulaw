import fitz
import sys
import io
import re
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

pdf_paths = {
    "03_국회_대통령": vp("3.공법", "_분할", "유니온헌법기출편_03_통치구조_국회_대통령.pdf"),
    "04_법원_헌법재판소": vp("3.공법", "_분할", "유니온헌법기출편_04_법원_헌법재판소.pdf")
}

md_paths = [
    vp("3.공법", "10.이진_헌법원리1", "유니온 마크다운", "유니온_기출_통치구조_국회_대통령.md"),
    vp("3.공법", "10.이진_헌법원리1", "유니온 마크다운", "유니온_기출_법원_헌법재판소.md")
]

target_nums = [
    1, 5, 6, 7, 8, 12, 13, 14, 15, 16, 17, 21, 24, 26, 27, 28, 32, 33, 39, 44, 45, 49, 51, 52, 58, 59, 61, 66, 67, 68,
    77, 78, 79, 80, 83, 84, 85, 86, 87, 88, 90, 91, 98, 99, 100, 107, 108, 109, 110, 111, 112, 113, 114, 130, 133, 134,
    140, 141, 142, 150, 151, 152, 155
]

# Load MD transcripts to build fallback answer map
md_answers = {}
for md_path in md_paths:
    if not os.path.exists(md_path):
        continue
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = r'(?:####+\s*\[?(?:20\d{2}년\s*)?(?:변시\s*)?헌법\s*문\s*(\d+)\]?|#####\s*【[^】]*문\s*(\d+)】)'
    matches = list(re.finditer(pattern, content))
    for i, m in enumerate(matches):
        q_num = int(m.group(1) or m.group(2))
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(content)
        sec_text = content[start:end]
        
        ans_find = re.search(r'([①-⑤])\s*.*정답\s*선지', sec_text)
        if not ans_find:
            ans_find = re.search(r'([①-⑤])\s*\(\s*X\s*\)\s*\[정답\]', sec_text)
        if not ans_find:
            ans_find = re.search(r'\*\*([①-⑤])\s*\(X\)', sec_text)
        if ans_find:
            md_answers[q_num] = ans_find.group(1)

# Exact answer key
known_answers = {
    1: "②", 5: "②", 6: "①", 7: "①", 8: "⑤", 12: "②", 13: "②", 14: "②", 15: "②", 16: "④", 17: "②",
    21: "④", 24: "③", 26: "④", 27: "①", 28: "③", 32: "②", 33: "①", 39: "③", 44: "①", 45: "①",
    49: "①", 51: "③", 52: "①", 58: "④", 59: "③", 61: "⑤", 66: "⑤", 67: "④", 68: "⑤",
    77: "④", 78: "②", 79: "③", 80: "③", 83: "④", 84: "⑤", 85: "④", 86: "①", 87: "①", 88: "①",
    90: "④", 91: "②", 98: "①", 99: "②", 100: "⑤", 107: "⑤", 108: "①", 109: "①", 110: "⑤",
    111: "⑤", 112: "⑤", 113: "①", 114: "④", 130: "②", 133: "①", 134: "③", 140: "③", 141: "②",
    142: "②", 150: "⑤", 151: "①", 152: "③", 155: "⑤"
}

final_answers = {}
for n in target_nums:
    final_answers[n] = known_answers.get(n) or md_answers.get(n) or "확인 필요"

# Load PDFs
print("Loading PDFs...")
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

q_03 = process_pdf(pdf_paths["03_국회_대통령"], ocr_replacements_03)
q_04 = process_pdf(pdf_paths["04_법원_헌법재판소"], ocr_replacements_04)

combined_q = {}
combined_q.update(q_03)
combined_q.update(q_04)

# Specific legal corrections
custom_corrections = {
    1: ["지방자치단체의 장에게 지방의회 사무직원 임용권을 부여하는 것은 권력분립원칙에 위배되지 않는다."],
    5: ["선거기간 중 선거에 영향을 미치게 하기 위해 25명을 초과하는 집회나 모임을 개최할 수 없도록 한 공직선거법 조항은 위헌이다.",
        "농협중앙회장 선거 및 선거운동권은 헌법상 보장되는 선거권의 범위에 포함되지 않는다."],
    6: ["지역구 국회의원 선거의 소선거구 다수대표제는 평등권과 선거권을 침해하지 않는다.",
        "선거방송토론위원회의 대담·토론회 초청 자격 제한은 평등권을 침해하지 않는다."],
    7: ["새마을금고 임원 선거에서 선거운동을 하는 권리는 헌법상 보장되는 선거권의 범위에 속하지 않는다.",
        "사적인 결사와 비교할 때 공적 역할을 수행하는 새마을금고 임원 선거의 경우 기본권 제한 시 완화된 비례성 기준이 적용될 수 있다."],
    8: ["대통령 및 국회의원 선거에서 확성장치 최고출력과 소음 규제기준을 두지 않은 공직선거법 조항은 건강하고 쾌적한 환경에서 생활할 권리를 침해한다.",
        "임기만료에 따른 비례대표 선거에서 정당에 배분된 비례대표 의석수가 추천한 후보자 수를 넘는 때에는 그 넘는 의석은 공석으로 한다."],
    12: ["국가공무원법상 '그 밖의 정치단체' 가입 금지는 명확성원칙에 위배된다(위헌).",
         "군무원의 정치적 표현 및 의견 공표 역시 군인의 지위에 준하여 공익적 차원에서 엄격한 제한을 받는다."],
    13: ["공무원의 집단행위 금지 조항 중 '공무 외의 일을 위한 집단행위'는 공익에 반하는 행위로서 직무전념의무를 해태하는 집단적 행위에 한정되어 합헌이다.",
         "교원의 정당 가입 및 정치단체 가입 전면 금지는 과잉금지원칙에 위배되어 정치적 표현 및 결사의 자유를 침해한다."],
    14: ["조례에 대한 법률의 위임은 포괄적인 위임도 허용되므로, 반드시 구체적으로 범위를 정하여 위임해야 하는 것은 아니다.",
         "지방자치단체의 장은 이송받은 조례안의 일부에 대하여 또는 조례안을 수정하여 재의를 요구할 수 없다."],
    15: ["지방자치단체의 자치사무에 대한 무분별한 감사는 허용되지 않으나, 사전 감사대상이 아니었더라도 위법성이 명백히 드러난 경우 감사대상을 추가·확장할 수 있다.",
         "조례 제정권 역시 헌법상 제도적으로 보장된 범위 내에 존재한다."],
    16: ["조례 제정·개폐청구권은 헌법상 열거되지 아니한 기본권이 아니라 법률에 의하여 보장되는 권리에 불과하다.",
         "조례에 위임할 사항은 행정입법에 위임할 사항보다 더 포괄적이어도 헌법에 반하지 않는다."],
    17: ["공유수면 해상경계선에 대한 명시적 법령이나 불문법이 없다면 형평의 원칙에 따라 헌법재판소가 경계를 확정하여야 한다.",
         "지방자치단체의 자치권이 미치는 범위에는 바다(공유수면)도 포함된다."],
    21: ["국회부의장은 헌법에 규정되어 있는 헌법기관이므로, 부의장을 3인으로 늘리려면 헌법개정이 필요하다.",
         "국회의원이 국회의장으로 당선된 때에는 당선된 다음 날부터 재직하는 동안 당적을 가질 수 없다(당적 이탈 의무)."],
    24: ["다수결 원칙에 따른 일반정족수가 헌법상 규정된 대의제 민주주의의 기본적이고도 핵심적인 정족수이나 절대적인 예외 없는 원칙은 아니다.",
         "일사부재의의 원칙은 헌법이 아닌 국회법에 명시된 법률상 규정이다."],
    26: ["국회의 입법권은 적법절차원칙으로부터 도출되는 청문절차 요구 등에 의하여 제한되지 아니한다.",
         "법률의 제·개정 행위를 다투는 권한쟁의심판은 국회의장에 대해서가 아니라 법률 제정권자인 '국회'를 피청구인으로 지정하여야 한다."],
    27: ["국회부의장은 헌법 제60조에 명시된 헌법기관이므로 부의장 인원 조정을 위해 헌법개정이 필요하다.",
         "국회의 동의권 침해와 국회의원의 심의·표결권 침해는 별개의 사안이며, 국회의원의 권한은 대외적 대립관계가 아닌 국회 내부 관계에서 행사된다."],
    28: ["대통령은 이송받은 법률안 중 특정 조항만 수정하거나 일부에 대해서만 재의를 요구할 수 없다.",
         "국회가 폐회 중이더라도 대통령은 15일 이내에 법률안의 환부 및 재의를 요구할 수 있다."],
    32: ["정부는 회계연도마다 예산안을 편성하여 회계연도 개시 120일 전까지 국회에 제출하여야 한다.",
         "국회의 예산안 의결은 일반 국민을 구속하지 않는 법규범이므로 헌법소원심판의 대상이 되지 않는다."],
    33: ["준예산은 헌법상 예산불성립 시 정부가 헌법 또는 법률에 의해 설치된 기관의 운영, 법률상 지출의무 이행을 위해 전년도 예산에 준해 집행할 수 있는 비상 지출제도이다.",
         "예산안에 대한 국회의 수정동의는 국회의원 30명 이상의 찬성(연서)이 있어야 발의할 수.있다."],
    39: ["국회 상임위원은 윤리심사자문위원회의 심사나 허가 여부와 상관없이 소관 상임위원회의 직무와 관련한 영리행위를 일절 할 수 없다.",
         "의원의 석방 요구는 국회 재적의원 4분의 1 이상의 연서로 발의하여야 한다."],
    77: ["상급법원 재판에서의 판단은 당해 사건에 한해서만 하급심을 기속하며, 동종의 다른 사건에는 기속력이 미치지 않는다.",
         "대법원 판결에 의해 명령·규칙이 위헌·위법임이 확정된 때에는 대법원은 지체없이 그 사유를 행정안전부장관에게 통보해야 한다."],
    140: ["정당이나 교섭단체는 권한쟁의심판의 당사자가 될 수 없지마는, 교섭단체는 국회의 부분기관이므로 권한쟁의심판 청구 불가하다.",
          "지방의회의원과 지방의회의장 간의 권한쟁의심판은 헌법재판소가 관장하는 지방자치단체 상호간의 권한쟁의 범위에 해당하지 않아 부적법하다."],
}

def parse_and_refine_question(num, raw_text, ans):
    # Extract Year
    year_match = re.search(r'(\d{2}\s*년\s*(?:변호사시험|변시|사법시험|사시))', raw_text)
    year = year_match.group(1).replace(" ", "") if year_match else ""
    
    # Separate question body from explanation
    expl_start_patterns = [r'lW뀔', r'l\s*W', r'훌훨훨', r'R야I', r'l\s*R', r'lW', r'l\s*M', r'l\s*활', r'l\s*뀐', r'\*\*']
    split_idx = len(raw_text)
    
    for pat in expl_start_patterns:
        m = re.search(pat, raw_text)
        if m and m.start() < split_idx:
            split_idx = m.start()
            
    question_part = raw_text[:split_idx]
    explanation_part = raw_text[split_idx:]
    
    question_part = clean_ocr_noise(question_part)
    explanation_part = clean_ocr_noise(explanation_part)
    
    # Normalize lines
    raw_lines = [l.strip() for l in question_part.split('\n') if l.strip()]
    
    circles = ["①", "②", "③", "④", "⑤"]
    box_letters = ["ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ"]
    
    circle_idx = 0
    box_idx = 0
    
    refined_lines = []
    for line in raw_lines:
        if f"문{num}" in line.replace(" ", "") or (year and year in line.replace(" ", "")):
            continue
            
        line_strip = line.strip()
        
        # Match circle option markers (and common OCR corruptions of them)
        m_circle = re.match(r'^([-•]?\s*)(@|①|②|③|④|⑤|CD|cz\)|㉠|㉡|㉢|㉣|㉤|㉮|㉯|㉰|㉱|㉲)\s*(.*)', line_strip, re.IGNORECASE)
        m_box = re.match(r'^([-•]?\s*)(ㄱ\.|ㄴ\.|ㄷ\.|ㄹ\.|ㅁ\.|ㄱ\s|ㄴ\s|ㄷ\s|ㄹ\s|ㅁ\s|ㄴ\s|ㄷ\s|ㄹ\s)\s*(.*)', line_strip)
        
        if m_circle:
            prefix = circles[circle_idx % 5]
            content = m_circle.group(3)
            refined_lines.append(f"{prefix} {content}")
            circle_idx += 1
        elif m_box:
            prefix = f"{box_letters[box_idx % 5]}."
            content = m_box.group(3)
            refined_lines.append(f"{prefix} {content}")
            box_idx += 1
        else:
            # Check for combination selection blocks at the end like "① 1, L" or "cz) L, 근"
            m_comb = re.match(r'^([①-⑤]|CD|cz\)|@|\([0-9]+\))\s*(.*)', line_strip, re.IGNORECASE)
            if m_comb:
                prefix = circles[circle_idx % 5]
                content = m_comb.group(2)
                refined_lines.append(f"{prefix} {content}")
                circle_idx += 1
            else:
                refined_lines.append(line_strip)
                
    # Format options, ensure only ONE correct answer highlight is applied per question
    body_formatted = ""
    bolded_ans = False
    
    for line in refined_lines:
        is_ans = False
        if ans != "확인 필요" and not bolded_ans:
            # Strict start check to avoid highlighting wrong lines
            if line.startswith(ans):
                is_ans = True
                bolded_ans = True
                
        if is_ans:
            body_formatted += f"**{line} (정답)**\n"
        else:
            body_formatted += f"{line}\n"
            
    # Corrections
    corrections = []
    if num in custom_corrections:
        corrections = custom_corrections[num]
    else:
        expl_lines = [l.strip() for l in explanation_part.split('\n') if l.strip()]
        for line in expl_lines:
            if "(X)" in line or "틀렸다" in line or "위반된다" in line or "침해한다" in line:
                clean = re.sub(r'^[-\s•①-⑤\(\)OX정답\[\]a-zA-Z가-힣\d\.]+', '', line).strip()
                clean = re.sub(r'\[\[.*?\]\]|\(.*?\)', '', clean).strip()
                if len(clean) > 20 and len(clean) < 120:
                    corrections.append(clean)
                    
    md = f"##### 【{year} 문{num}】 (정답: **{ans}**)\n"
    md += body_formatted.strip() + "\n"
    if corrections:
        md += "\n* **오답 바로잡기 (옳은 문장)**:\n"
        for corr in list(set(corrections))[:2]:
            md += f"  - {corr}\n"
    md += "\n---\n\n"
    return md

# Compile final cleansed markdown
final_markdown = "# 유니온 헌법 기출 제3편 통치구조 문제 초간결 정제본\n\n"
for num in target_nums:
    ans = final_answers.get(num, "확인 필요")
    if num in combined_q:
        final_markdown += parse_and_refine_question(num, combined_q[num], ans)
    else:
        final_markdown += f"##### 【문{num}】 (미확인)\nPDF 소스에서 문항을 찾을 수 없습니다.\n\n---\n\n"

# Save
out_path = r"C:\Users\111\.gemini\antigravity\scratch\final_questions.md"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(final_markdown)

print("Cleansed markdown generated successfully!")
