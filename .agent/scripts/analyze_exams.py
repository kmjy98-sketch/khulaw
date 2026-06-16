import os
import re
import sys
import io

# Fix encoding for Windows stdout
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', errors='ignore')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8', errors='ignore')

# Keywords for each category in Part 1 scope
KEYWORDS = [
    "사명", "상인", "공공성", "영업성", "세무", "변리", "중개", "등록", "결격", 
    "실무수습", "개업", "사무소", "사무직원", "법무법인", "법무조합", "공동사무소", "합동법률"
]

def analyze_exam_file(filepath):
    print(f"\n=== Analyzing {os.path.basename(filepath)} ===")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split content by questions like "문 1.", "문  2.", "문\s+\d+\."
    questions = re.split(r'(?m)^문\s*(\d+)\.', content)
    
    # The first element is header
    header = questions[0]
    matched_questions = []
    
    for i in range(1, len(questions), 2):
        q_num = questions[i]
        q_text = questions[i+1] if i+1 < len(questions) else ""
        
        # Check if any keyword matches
        matches = [kw for kw in KEYWORDS if kw in q_text]
        if matches:
            # Clean text for preview
            preview = q_text.strip().split("\n")[0]
            if len(preview) > 100:
                preview = preview[:100] + "..."
            matched_questions.append((q_num, matches, preview))
            
    for q_num, matches, preview in matched_questions:
        print(f"문 {q_num} (매칭 키워드: {', '.join(matches)}) -> {preview}")
    return matched_questions

def main():
    scratch_dir = "C:/Users/111/.gemini/antigravity/scratch"
    exam_files = [
        "법조윤리_한권탁_2024_중간고사_문제.txt",
        "법조윤리_한권탁_2024_기말고사_문제.txt",
        "법조윤리_한권탁_2025_기말고사_문제.txt"
    ]
    
    for filename in exam_files:
        filepath = os.path.join(scratch_dir, filename)
        if os.path.exists(filepath):
            analyze_exam_file(filepath)

if __name__ == "__main__":
    main()
