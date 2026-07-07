# -*- coding: utf-8 -*-
"""
유형번호 일괄 적용 스크립트
typed_files.json의 to_rename 리스트를 기반으로 파일명 변경
"""
import os
import json

root_path = r"H:\내 드라이브"
input_file = os.path.join(root_path, ".agent", "typed_files.json")
log_file = os.path.join(root_path, ".agent", "type_rename_log.json")

# Load typed files
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

results = {
    'renamed': [],
    'errors': []
}

for item in data['to_rename']:
    original_path = item['original_path']
    new_path = item['new_path']
    
    if not os.path.exists(original_path):
        results['errors'].append({
            'path': original_path,
            'error': 'File not found'
        })
        continue
    
    if os.path.exists(new_path):
        results['errors'].append({
            'path': original_path,
            'error': 'Target file already exists'
        })
        continue
    
    try:
        os.rename(original_path, new_path)
        results['renamed'].append({
            'original': original_path,
            'new': new_path,
            'type': item['type']
        })
    except Exception as e:
        results['errors'].append({
            'path': original_path,
            'error': str(e)
        })

# Save log
with open(log_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"=== 이름 변경 결과 ===")
print(f"성공: {len(results['renamed'])}개")
print(f"오류: {len(results['errors'])}개")
print(f"\n상세 로그: {log_file}")
