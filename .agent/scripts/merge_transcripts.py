
import os
import re

# 경로 설정
src_dir = "h:/내 드라이브"
dest_dir = "h:/내 드라이브/민사"
if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)

# 파일 패턴
base_filename = "5-00_민법_송영곤_기본민법_전사문"
output_filename = "5-00_민법_송영곤_기본민법_10회차_통합.md"
output_path = os.path.join(dest_dir, output_filename)

# 오타 수정 맵
replacements = {
    "선을 이제": "수업을 이제",
    "선멸시효": "소멸시효",
    "소멸시 ": "소멸시효 ",
    "소멸시가": "소멸시효가",
    "소멸시는": "소멸시효는",
    "소멸시의": "소멸시효의",
    "소멸시와": "소멸시효와",
    "소멸시도": "소멸시효도",
    "소멸시에": "소멸시효에",
    "수송으로": "소송으로",
    "대어금": "대여금",
    "제재변": "재재항변",
    "기선점": "기산점",
    "기사일": "기산일",
    "혜태": "해태",
    "회태": "해태",
    "임무 회태": "임무 해태",
    "임무 혜태": "임무 해태",
    "손해 배상": "손해배상",
    "채무 불량": "채무불이행",
    "침불행": "채무불이행",
    "채무 불행": "채무불이행",
    "채무불행": "채무불이행",
    "채무 분량": "채무불이행",
    "소구 채권": "소구채권",
    "유약금": "위약금",
    "유약벌": "위약벌",
    "사적 제재": "사적 제재",
    "금융스": "금융리스",
    "금융리스": "금융리스",
    "리조트 사용": "리조트 사용료",
    "동가리": "돈거래",
    "면책적 체면서": "면책적 채무인수",
    "면책적 채무인서는": "면책적 채무인수는",
    "면적지 채무인수": "면책적 채무인수",
    "면적 채무수": "면책적 채무인수",
    "부정성": "부종성",
    "비수닥 보증": "비수탁 보증인",
    "수탁 보증인": "수탁보증인",
    "물산 보증": "물상보증",
    "물상보증인": "물상보증인",
    "기한 익상실": "기한이익 상실",
    "기한이익상실": "기한이익 상실",
    "주인법": "주임법",
    "자배법": "자배법",
    "가집 선거": "가집행 선고",
    "가집행 선고": "가집행 선고",
    "사변종": "사실심 변론종결",
    "사시 변론 종결": "사실심 변론종결",
    "보안 판결": "본안 판결",
    "기판력": "기판력", 
    "기발력": "기판력",
    "기팔력": "기판력",
    "지금 명령": "지급명령",
    "지급 영령": "지급명령",
    "지급영령": "지급명령",
    "집행 권원": "집행권원",
    "집행 고론": "집행권원",
    "집행권원": "집행권원",
    "독적 절차": "독촉절차",
    "독척": "독촉",
    "구채무": "구채무",
    "신채무": "신채무",
    "동시성": "동일성",
    "경계나": "경개나",
}

def clean_text(text):
    # 1. 오타 수정
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # 2. 문장 부호 정리
    text = text.replace("어,", "").replace("저기,", "").replace("그,", "") 
    
    # 3. 문단 나누기 (마침표 뒤에 줄바꿈 추가)
    # 단순히 마침표만으로 나누면 너무 잘게 쪼개질 수 있으니, 
    # "자," "그래서" "그러나" 등으로 시작하는 문장 앞에서 줄바꿈을 한 번 더 해줌.
    
    sentences = text.split(". ")
    new_text = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence: continue
        
        # 문장 끝에 마침표 복구 (split으로 사라짐)
        if not sentence.endswith("."):
            sentence += "."
            
        new_text += sentence + " "
        
        # 특정 접속사나 화제 전환어 앞에서 줄바꿈
        if sentence.startswith("자,") or sentence.startswith("그래서") or sentence.startswith("그런데") or sentence.startswith("하지만") or sentence.startswith("동그라미"):
            new_text += "\n\n"
        elif len(new_text.split("\n")[-1]) > 150: # 한 문단이 너무 길면 줄바꿈
             new_text += "\n"
             
    return new_text

def format_as_markdown(text):
    # 간단한 구조화: "자," 로 시작하는 문단 중 핵심 키워드가 있는 경우 헤더 처리 시도 (어려움)
    # 대신 전체를 깔끔하게 정리.
    
    lines = text.split("\n")
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            formatted_lines.append("")
            continue
            
        # 소제목 후보 식별 (예: "자 165조를 보도록 하죠")
        if re.match(r"^자\s*(\d+조|.*?에 관해서|.*?를 보도록 하죠).*", line):
             formatted_lines.append(f"\n## {line.replace('자 ', '')}\n")
        else:
             formatted_lines.append(line)
             
    return "\n".join(formatted_lines)

# 병합 실행
full_content = ""
# (1)번부터 (8)번까지 순서대로
for i in range(1, 9):
    filename = f"{base_filename} ({i}).md"
    filepath = os.path.join(src_dir, filename)
    
    if os.path.exists(filepath):
        print(f"Reading {filename}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # 메타데이터 라인 제거 (Line number prefix removal if exists from tool output? No, files are raw text usually. 
            # But the view_file tool output showed line numbers, actual file likely doesn't have them unless tool added them.
            # Assuming raw file content.)
            full_content += content + "\n"
    else:
        print(f"File not found: {filename}")

# 정제
cleaned_content = clean_text(full_content)
formatted_content = format_as_markdown(cleaned_content)

# 헤더 추가
header = """# 민법 강의노트 (송영곤 기본민법 10회차)
- 일시: 2026년 10월 26일
- 주제: 소멸시효 (기산점, 기간, 중단, 정지 등)

---
"""

final_output = header + formatted_content

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(final_output)

print(f"Successfully created {output_path}")
