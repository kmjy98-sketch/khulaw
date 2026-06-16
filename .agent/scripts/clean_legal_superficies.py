import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

input_file = r"C:\Users\111\.gemini\antigravity\scratch\extracted_highlights\법정지상권_highlights.md"
output_file = r"C:\Users\111\.gemini\antigravity\scratch\extracted_highlights\법정지상권_highlights_clean.md"

if not os.path.exists(input_file):
    print("Input file does not exist.")
    sys.exit(1)

with open(input_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

cleaned_sentences = []
seen_normalized = set()

current_source = ""
current_page = ""

for line in lines:
    line_str = line.strip()
    if not line_str:
        continue
    
    if line_str.startswith("### 출처:"):
        match = re.search(r"### 출처:\s*(.*?)\s*\((## Page \d+)\)", line_str)
        if match:
            current_source = match.group(1).strip()
            current_page = match.group(2).strip()
        continue
    
    if line_str.startswith("-"):
        sentence = line_str.replace("-", "", 1).strip()
        
        # Filter out very short fragments
        if len(sentence) <= 3:
            continue
            
        # Normalize for deduplication
        normalized = re.sub(r"[^\w]", "", sentence)
        
        # Additional cleanup for odd symbols that might break text
        # e.g., parenthetical characters, strange artifacts
        
        if normalized not in seen_normalized:
            seen_normalized.add(normalized)
            cleaned_sentences.append({
                'text': sentence,
                'source': f"{current_source} ({current_page})"
            })

output_lines = [
    "# 법정지상권 파트 형광펜 발췌 (중복 제거 및 정제본)\n",
    "이 문서는 추출된 법정지상권 관련 형광펜 문장들 중 중복을 제거하고 의미 있는 문장 단위로 정제한 결과입니다.\n"
]

for idx, item in enumerate(cleaned_sentences):
    output_lines.append(f"{idx+1}. {item['text']}  *(출처: {item['source']})*")

with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"Cleaned highlights saved to {output_file}")
print(f"Total unique sentences: {len(cleaned_sentences)}")
