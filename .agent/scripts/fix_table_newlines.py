import os

TARGET_LIST = r'C:\Users\111\.gemini\antigravity\brain\add3c14b-36a5-488b-be51-fb847d79f19e\scratch\broken_tables_files.txt'
BASE_DIR = r'H:\내 드라이브\sync'

def fix_newlines_around_tables(content):
    lines = content.split('\n')
    out = []
    in_table = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 블록인용구 내부에 있는 표는 건드리지 않음 (옵시디언 콜아웃 등에서 문제없음)
        if line.lstrip().startswith('>'):
            if in_table:
                in_table = False
                # 만약 이전 줄까지 표였고, 지금 인용구가 시작된다면 표와 인용구 사이에 빈 줄을 넣는 것이 좋음
                if stripped != '':
                    out.append('')
            out.append(line)
            continue
            
        is_row = stripped.startswith('|') and stripped.endswith('|') and stripped.count('|') > 1
        
        if is_row:
            if not in_table:
                # 표가 시작됨. 바로 윗줄이 빈 줄이 아니면 빈 줄 삽입
                if len(out) > 0:
                    prev_out = out[-1].strip()
                    if prev_out != '' and not prev_out.startswith('>'):
                        out.append('')
                in_table = True
            out.append(line)
        else:
            if in_table:
                # 표가 끝남. 현재 줄이 빈 줄이 아니면 빈 줄 삽입 후 현재 줄 추가
                in_table = False
                if stripped != '':
                    out.append('')
            out.append(line)
            
    return '\n'.join(out)

def process_all():
    with open(TARGET_LIST, 'r', encoding='utf-8') as f:
        target_files = [line.strip() for line in f if line.strip()]
        
    fixed_count = 0
    for rel_path in target_files:
        full_path = os.path.join(BASE_DIR, rel_path)
        if not os.path.exists(full_path):
            continue
            
        with open(full_path, 'r', encoding='utf-8') as f:
            original = f.read()
            
        fixed = fix_newlines_around_tables(original)
        
        if original != fixed:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(fixed)
            fixed_count += 1
            print(f"Fixed newlines: {rel_path}")
            
    print(f"\nProcessing complete. Fixed newlines in {fixed_count} files.")

if __name__ == '__main__':
    process_all()
