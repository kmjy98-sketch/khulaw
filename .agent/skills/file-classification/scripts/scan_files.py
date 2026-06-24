import os
import re
import json
import sys

# 출력 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

TARGET_DIRS = [
    r"E:\법학볼트\1.민사",
    r"E:\법학볼트\2.형사",
    r"E:\법학볼트\3.공법",
    r"E:\법학볼트\5.기타",
]

EXCLUDE_EXT = {'.ini', '.json', '.py', '.ps1', '.bat', '.xml', '.db'}
EXCLUDE_NAMES = {'SKILL.md', 'task.md', 'README.md', '.DS_Store'}
EXCLUDE_DIRS = {'.agent', '_trash', '원본 워크플로우'}

# (1-01), (2-10), (5-00) 등의 패턴 확인
pattern = re.compile(r'^\(\d+-\d+\)')

violation_files = []

for root_dir in TARGET_DIRS:
    if not os.path.exists(root_dir):
        continue
        
    for root, dirs, files in os.walk(root_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            name, ext = os.path.splitext(file)
            if ext.lower() in EXCLUDE_EXT:
                continue
            if file in EXCLUDE_NAMES:
                continue
            
            # .gdoc, .gsheet 등 구글 문서 파일은 제외할 수도 있으나 확인용으로 포함
            
            if not pattern.match(file):
                violation_files.append({
                    "path": os.path.join(root, file),
                    "name": file
                })

# 파일로 저장
with open(r'E:\법학볼트\.agent\violation_report.json', 'w', encoding='utf-8') as f:
    json.dump(violation_files, f, ensure_ascii=False, indent=2)

print(f"Scan complete. Found {len(violation_files)} violations.")
