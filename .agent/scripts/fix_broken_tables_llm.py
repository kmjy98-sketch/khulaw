import os
import sys
import json
import time
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

try:
    import google.generativeai as genai
except ImportError:
    print("google-generativeai 패키지가 없습니다. pip install google-generativeai 를 실행하세요.")
    exit(1)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    system_instruction="당신은 최고 수준의 법학 전공 텍스트 에디터입니다."
)

BASE_DIR = vp("sync")
PROMPT_PATH = vp(".agent", "lib", "_reflow_prompt_standard.md")
TARGET_LIST_PATH = r"C:\Users\111\.gemini\antigravity\brain\add3c14b-36a5-488b-be51-fb847d79f19e\scratch\broken_tables_files.txt"
STATE_FILE = r"C:\Users\111\.gemini\antigravity\brain\add3c14b-36a5-488b-be51-fb847d79f19e\scratch\fix_tables_state.json"

def load_prompt():
    with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
        base_prompt = f.read()
    
    # 표 복구 관련 추가 지침 삽입
    extra_instruction = """
#### 4-7. 깨진 표 복구 (가장 중요)
- 원본에서 `|` 기호가 연속적으로 등장하거나, 내용상 표(Table)로 존재해야 했던 부분이 줄글로 뭉쳐져 있는 경우(`POSSIBLE_BROKEN_TABLE_INLINE`, `BROKEN_TABLE_NO_SEPARATOR`) 완벽한 마크다운 표 문법(`|---|---|`)을 사용하여 표를 복원하세요.
- 열(Column) 개수가 어긋난 표(`TABLE_COLUMN_MISMATCH`)도 열 개수를 올바르게 맞춰 복구하세요.
"""
    return base_prompt + "\n" + extra_instruction

def process_file_with_llm(file_path, prompt_template):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"File read error: {e}")
        return None

    filename = os.path.basename(file_path)
    prompt = prompt_template.replace("{FILE_PATH}", file_path)\
                            .replace("{BOOK_FULL_NAME}", "교재원문")\
                            .replace("{CHAPTER_TOPIC}", filename)\
                            .replace("{PREVIOUS_CHUNK_TAIL}", "(이전 청크 정보 없음)")
                            
    full_prompt = f"{prompt}\n\n[원본 마크다운 텍스트 시작]\n{content}\n[원본 마크다운 텍스트 끝]"
    
    try:
        response = model.generate_content(full_prompt)
        text = response.text
        if text.startswith("```markdown"): text = text[11:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        return text.strip()
    except Exception as e:
        print(f"[{filename}] API Error: {e}")
        return None

def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        return
        
    prompt_template = load_prompt()
    
    with open(TARGET_LIST_PATH, 'r', encoding='utf-8') as f:
        target_files = [line.strip() for line in f if line.strip()]
        
    # 진행 상태 로드
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
            
    pending_files = [f for f in target_files if state.get(f) != 'ok']
    print(f"Total files: {len(target_files)}, Pending: {len(pending_files)}")
    
    # 배치 처리를 위한 그룹핑 (일반/민법/형법/헌법)
    batch1 = [] # 일반 폴더 및 자소서
    batch2 = [] # 민법
    batch3 = [] # 형법
    batch4 = [] # 헌법
    
    for f in pending_files:
        if f.startswith('_교재원문\\민법'): batch2.append(f)
        elif f.startswith('_교재원문\\형법'): batch3.append(f)
        elif f.startswith('_교재원문\\헌법'): batch4.append(f)
        else: batch1.append(f)
        
    print(f"Batch 1 (General): {len(batch1)}")
    print(f"Batch 2 (Civil Law): {len(batch2)}")
    print(f"Batch 3 (Criminal Law): {len(batch3)}")
    print(f"Batch 4 (Constitutional Law): {len(batch4)}")
    
    # 실행할 배치를 사용자 입력을 받지 않고 우선 Batch 1부터 실행
    # (본 스크립트는 여러 번 실행되도록 설계)
    
    targets = batch1 + batch2 + batch3 + batch4
    if not targets:
        print("모든 파일 처리가 완료되었습니다.")
        return

    print("복구 처리를 시작합니다...")
    for rel_path in targets:
        full_path = os.path.join(BASE_DIR, rel_path)
        print(f"-> 처리 중: {rel_path}")
        
        if not os.path.exists(full_path):
            print(f"  [오류] 파일을 찾을 수 없습니다: {full_path}")
            state[rel_path] = 'not_found'
            continue
            
        result = process_file_with_llm(full_path, prompt_template)
        if result and len(result) > 300:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(result)
            state[rel_path] = 'ok'
            print("   [성공]")
        else:
            state[rel_path] = 'fail'
            print("   [실패] 결과가 너무 짧거나 에러 발생")
            
        # 상태 저장
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            
        time.sleep(3)

if __name__ == "__main__":
    main()
