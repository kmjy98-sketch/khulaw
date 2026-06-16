import os
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', errors='ignore')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8', errors='ignore')

def get_question_and_answer(exam_txt, exp_txt, target_nums):
    results = []
    
    with open(exam_txt, "r", encoding="utf-8") as f:
        exam_content = f.read()
    with open(exp_txt, "r", encoding="utf-8") as f:
        exp_content = f.read()
        
    # Split by questions
    exam_qs = re.split(r'(?m)^문\s*(\d+)\.', exam_content)
    exp_qs = re.split(r'(?m)^문\s*(\d+)\.', exp_content)
    
    exam_dict = {}
    for i in range(1, len(exam_qs), 2):
        exam_dict[exam_qs[i].strip()] = exam_qs[i+1].strip()
        
    exp_dict = {}
    for i in range(1, len(exp_qs), 2):
        exp_dict[exp_qs[i].strip()] = exp_qs[i+1].strip()
        
    for num in target_nums:
        str_num = str(num)
        q_text = exam_dict.get(str_num, "Not Found")
        ans_text = exp_dict.get(str_num, "Not Found")
        
        results.append(f"### [문 {num}]\n\n**[문제]**\n{q_text}\n\n**[정답 및 해설]**\n{ans_text}\n\n---\n")
        
    return "\n".join(results)

def main():
    scratch_dir = "C:/Users/111/.gemini/antigravity/scratch"
    
    # 2024 Midterm
    mid_2024_q = os.path.join(scratch_dir, "법조윤리_한권탁_2024_중간고사_문제.txt")
    mid_2024_a = os.path.join(scratch_dir, "법조윤리_한권탁_2024_중간고사_정답_및_해설.txt")
    mid_2024_targets = [3, 9, 14, 18, 29]
    
    # 2024 Final
    fin_2024_q = os.path.join(scratch_dir, "법조윤리_한권탁_2024_기말고사_문제.txt")
    fin_2024_a = os.path.join(scratch_dir, "법조윤리_한권탁_2024_기말고사_정답_및_해설.txt")
    fin_2024_targets = [14, 20, 26]
    
    # 2025 Final
    fin_2025_q = os.path.join(scratch_dir, "법조윤리_한권탁_2025_기말고사_문제.txt")
    fin_2025_a = os.path.join(scratch_dir, "법조윤리_한권탁_2025_기말고사_해설.txt")
    fin_2025_targets = [9, 29, 39]
    
    output = []
    
    if os.path.exists(mid_2024_q) and os.path.exists(mid_2024_a):
        output.append("## 2024 한권탁 중간고사\n")
        output.append(get_question_and_answer(mid_2024_q, mid_2024_a, mid_2024_targets))
        
    if os.path.exists(fin_2024_q) and os.path.exists(fin_2024_a):
        output.append("## 2024 한권탁 기말고사\n")
        output.append(get_question_and_answer(fin_2024_q, fin_2024_a, fin_2024_targets))
        
    if os.path.exists(fin_2025_q) and os.path.exists(fin_2025_a):
        output.append("## 2025 한권탁 기말고사\n")
        output.append(get_question_and_answer(fin_2025_q, fin_2025_a, fin_2025_targets))
        
    out_path = os.path.join(scratch_dir, "target_questions_summary.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print(f"Extraction complete. Saved to {out_path}")

if __name__ == "__main__":
    main()
