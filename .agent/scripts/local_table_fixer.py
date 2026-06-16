import os
import re
import json

TARGET_LIST_PATH = r"C:\Users\111\.gemini\antigravity\brain\add3c14b-36a5-488b-be51-fb847d79f19e\scratch\broken_tables_files.txt"
BASE_DIR = r"H:\내 드라이브\sync"

def fix_table_formats(content):
    lines = content.split('\n')
    out = []
    
    # 1. 인라인 줄글 표 복구 (POSSIBLE_BROKEN_TABLE_INLINE)
    # 여러 줄이 연속으로 | 를 포함하고 있으면 표로 감싼다
    temp_lines = []
    for line in lines:
        stripped = line.strip()
        # | 로 시작하거나 끝나지 않지만 중간에 | 가 있는 경우
        if '|' in stripped and not stripped.startswith('|') and not stripped.endswith('|') and not stripped.startswith('#') and not stripped.startswith('>'):
            temp_lines.append(f"| {stripped} |")
        else:
            temp_lines.append(line)
            
    lines = temp_lines
    out = []
    in_table = False
    
    # 2. 구분선 누락 및 구조 복구 (BROKEN_TABLE_NO_SEPARATOR)
    for i, line in enumerate(lines):
        stripped = line.strip()
        is_row = stripped.startswith('|') and stripped.endswith('|') and stripped.count('|') > 1
        is_sep = is_row and re.match(r'^\|[\s\-:|]+\|$', stripped)
        
        if is_row and not is_sep:
            if not in_table:
                in_table = True
                out.append(line)
                
                if i + 1 < len(lines):
                    next_stripped = lines[i+1].strip()
                    next_is_row = next_stripped.startswith('|') and next_stripped.endswith('|') and next_stripped.count('|') > 1
                    next_is_sep = next_is_row and re.match(r'^\|[\s\-:|]+\|$', next_stripped)
                    
                    if next_is_row and not next_is_sep:
                        # 누락된 구분선 삽입
                        cols = stripped.count('|') - 1
                        out.append('|' + '|'.join(['---'] * cols) + '|')
            else:
                # 기존 표의 데이터 행 열 개수 맞추기 로직
                # 첫 번째 행(헤더)의 열 개수를 추적해서 모자란 파이프를 채우는 것은 너무 복잡할 수 있으므로
                # 일단 그대로 추가
                out.append(line)
        elif is_sep:
            in_table = True
            out.append(line)
        else:
            in_table = False
            out.append(line)
            
    return '\n'.join(out)

def process_all():
    with open(TARGET_LIST_PATH, 'r', encoding='utf-8') as f:
        target_files = [line.strip() for line in f if line.strip()]
        
    print(f"Total files to process: {len(target_files)}")
    fixed_count = 0
    
    for rel_path in target_files:
        full_path = os.path.join(BASE_DIR, rel_path)
        if not os.path.exists(full_path):
            print(f"File not found: {full_path}")
            continue
            
        with open(full_path, 'r', encoding='utf-8') as f:
            original = f.read()
            
        fixed = fix_table_formats(original)
        
        if original != fixed:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(fixed)
            fixed_count += 1
            print(f"Fixed: {rel_path}")
            
    print(f"\nProcessing complete. Fixed {fixed_count} files.")

if __name__ == '__main__':
    process_all()
