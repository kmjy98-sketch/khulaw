import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

dir_path = r"C:\Users\111\.gemini\antigravity\scratch\extracted_highlights"
output_file = os.path.join(dir_path, "법정지상권_highlights.md")

extracted_data = []

files = [f for f in os.listdir(dir_path) if f.endswith(".md") and f != "법정지상권_highlights.md"]

for file in files:
    file_path = os.path.join(dir_path, file)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    pages = re.split(r"(## Page \d+)", content)
    if len(pages) < 2:
        continue
        
    for i in range(1, len(pages), 2):
        page_header = pages[i].strip()
        page_content = pages[i+1].strip()
        
        lines = page_content.split("\n")
        relevant_lines = []
        
        for line in lines:
            if not line.strip().startswith("-"):
                continue
            text = line.replace("-", "", 1).strip()
            
            # Filter for statutory superficies (법정지상권) keywords
            # "법정지상" matches "법정지상권", "법정지상권의" etc.
            # "관습법상" matches "관습법상 법정지상권" etc.
            # "366조" matches "제366조"
            if any(kw in text for kw in ["법정지상", "관습법상", "366조"]):
                relevant_lines.append(text)
            elif "지상권" in text and not any(x in text for x in ["구분지상권", "분묘기지권"]):
                # Include general superficies sentences if they appear in a relevant context
                relevant_lines.append(text)
                
        if relevant_lines:
            extracted_data.append({
                'source': file.replace("_highlights.md", ""),
                'page': page_header,
                'sentences': relevant_lines
            })

markdown_output = ["# 법정지상권 파트 형광펜 발췌 (문장 단위)\n"]

for item in extracted_data:
    markdown_output.append(f"### 출처: {item['source']} ({item['page']})")
    for s in item['sentences']:
        markdown_output.append(f"- {s}")
    markdown_output.append("")

with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(markdown_output))

print(f"Successfully filtered 법정지상권 highlights to {output_file}")
print(f"Total sections found: {len(extracted_data)}")
