# -*- coding: utf-8 -*-
"""
사본 파일 이름 변경 스크립트
- "~의 사본 (N).ext" → "~.ext" 형식으로 변경
- 중복 파일은 _trash/중복/ 폴더로 이동
"""
import os
import re
import json
import shutil
from datetime import datetime

root_path = r"H:\내 드라이브"
trash_folder = os.path.join(root_path, "_trash", "중복")
log_file = os.path.join(root_path, ".agent", "rename_log.json")

# Ensure trash folder exists
os.makedirs(trash_folder, exist_ok=True)

# Load copy files
with open(os.path.join(root_path, ".agent", "copy_files.json"), 'r', encoding='utf-8') as f:
    copy_files = json.load(f)

def clean_filename(filename):
    """Remove '의 사본' patterns from filename"""
    # Patterns to remove, in order of specificity:
    # 1. "의 사본의 사본 (N)" or "의 사본 (N)"
    # 2. "의 사본의 사본" or "의 사본"
    # 3. " 사본" (space before)
    # 4. "_사본"
    
    name, ext = os.path.splitext(filename)
    
    # Handle cases like ".pdf의 사본.pdf" where there are double extensions
    # Find the real original extension
    patterns = [
        r'\.pdf의 사본의 사본 \(\d+\)$',
        r'\.pdf의 사본 \(\d+\)$',
        r'\.pdf의 사본의 사본$',
        r'\.pdf의 사본$',
        r'\.docx\.pdf의 사본의 사본 \(\d+\)$',
        r'\.docx\.pdf의 사본 \(\d+\)$',
        r'\.docx\.pdf의 사본의 사본$',
        r'\.docx\.pdf의 사본$',
        r'\.docx의 사본의 사본 \(\d+\)$',
        r'\.docx의 사본 \(\d+\)$',
        r'\.docx의 사본의 사본$',
        r'\.docx의 사본$',
        r'\.hwp의 사본의 사본 \(\d+\)$',
        r'\.hwp의 사본 \(\d+\)$',
        r'\.hwp의 사본의 사본$',
        r'\.hwp의 사본$',
        r'의 사본의 사본 \(\d+\)$',
        r'의 사본 \(\d+\)$',
        r'의 사본의 사본$',
        r'의 사본$',
        r' 사본$',
        r'_사본$',
    ]
    
    clean_name = name
    for pattern in patterns:
        clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)
    
    # Handle case where extension was embedded in the name
    # e.g., "file.pdf의 사본" → name="file.pdf의 사본", ext=".pdf"
    # After cleaning → clean_name="file" + ext=".pdf" → "file.pdf"
    
    return clean_name + ext

def get_unique_path(path):
    """Get a unique path by adding timestamp if file exists"""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{timestamp}{ext}"

# Process files
results = {
    "renamed": [],
    "moved_to_trash": [],
    "errors": []
}

for file_info in copy_files:
    original_path = file_info['path']
    original_name = file_info['original_name']
    directory = file_info['dir']
    
    if not os.path.exists(original_path):
        results['errors'].append({
            'file': original_path,
            'error': 'File not found'
        })
        continue
    
    # Clean the filename
    new_name = clean_filename(original_name)
    new_path = os.path.join(directory, new_name)
    
    # If the new name is the same as original, skip
    if new_name == original_name:
        results['errors'].append({
            'file': original_path,
            'error': 'Could not clean filename'
        })
        continue
    
    try:
        # Check if target file already exists (it's a duplicate)
        if os.path.exists(new_path):
            # Move to trash as duplicate
            trash_path = os.path.join(trash_folder, original_name)
            trash_path = get_unique_path(trash_path)
            shutil.move(original_path, trash_path)
            results['moved_to_trash'].append({
                'original': original_path,
                'trash_path': trash_path,
                'reason': 'duplicate'
            })
        else:
            # Rename the file
            os.rename(original_path, new_path)
            results['renamed'].append({
                'original': original_path,
                'new': new_path
            })
    except Exception as e:
        results['errors'].append({
            'file': original_path,
            'error': str(e)
        })

# Save log
with open(log_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# Print summary
print(f"=== 이름 변경 결과 ===")
print(f"성공적으로 이름 변경: {len(results['renamed'])}개")
print(f"중복으로 휴지통 이동: {len(results['moved_to_trash'])}개")
print(f"오류 발생: {len(results['errors'])}개")
print(f"\n상세 로그: {log_file}")
