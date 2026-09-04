# -*- coding: utf-8 -*-
"""
유형번호 자동 부여 스크립트
분류 규칙:
  (1) 교재 - 교재, 책 원본, 강의자료
  (2) 정리 - 주요쟁점 정리, 기초법리, 요약
  (3) 사례 - 사례형 문제/풀이
  (4) 선택 - 선택형, DT 문제
  (5) 기타 - 위 분류 외 자료
"""
import os
import re
import json
from collections import defaultdict

root_path = r"H:\내 드라이브"
input_file = os.path.join(root_path, ".agent", "untyped_files.json")
output_file = os.path.join(root_path, ".agent", "typed_files.json")
log_file = os.path.join(root_path, ".agent", "type_assign_log.json")

# Load untyped files
with open(input_file, 'r', encoding='utf-8') as f:
    untyped_files = json.load(f)

# Type classification keywords
TYPE_KEYWORDS = {
    1: {  # 교재
        'keywords': ['교재', '민법의맥', '형법총론', '집행법', '샘플', '강의자료', '논점', 
                     '사례연습', '진도표', '강의계획서', '기출'],
        'size_threshold': 10 * 1024 * 1024,  # 10MB 이상
        'folder_keywords': ['교재']
    },
    2: {  # 정리
        'keywords': ['정리', '주요쟁점', '기초법리', '요약', '개관', '선택형자료'],
        'folder_keywords': []
    },
    3: {  # 사례
        'keywords': ['사례', '문제', '답안', '해설', '상세해설', '실전답안'],
        'folder_keywords': []
    },
    4: {  # 선택
        'keywords': ['선택형', 'DT', 'dt'],
        'folder_keywords': ['필기']
    },
    5: {  # 기타
        'keywords': ['필기노트', '전사문', '보충자료', '참고', '가이드'],
        'folder_keywords': ['전사문', '필기', '참고자료']
    }
}

def get_file_size(path):
    try:
        return os.path.getsize(path)
    except:
        return 0

def determine_type(file_info):
    """Determine the type number based on filename and folder"""
    filename = file_info['filename'].lower()
    folder = file_info['dir'].lower()
    path = file_info['path']
    
    # Check folder-based classification first
    if '전사문' in folder:
        return 5
    if '참고자료' in folder:
        return 5
    
    # Keyword-based classification
    for type_num in [1, 2, 3, 4, 5]:
        type_info = TYPE_KEYWORDS[type_num]
        
        # Check folder keywords
        for fk in type_info.get('folder_keywords', []):
            if fk.lower() in folder:
                # Also check filename keywords to be more specific
                for kw in type_info['keywords']:
                    if kw.lower() in filename:
                        return type_num
        
        # Check filename keywords
        for kw in type_info['keywords']:
            if kw.lower() in filename:
                return type_num
    
    # Size-based for type 1 (교재)
    if path.endswith('.pdf'):
        size = get_file_size(path)
        if size > TYPE_KEYWORDS[1]['size_threshold']:
            return 1
    
    # Default to 5 (기타)
    return 5

def get_next_sequence(type_counters, type_num, subject):
    """Get next sequence number for a type+subject combo"""
    key = (type_num, subject)
    type_counters[key] = type_counters.get(key, 0) + 1
    return type_counters[key]

def extract_subject(file_info):
    """Extract subject (과목) from path"""
    path = file_info['path']
    if '민사' in path or '민법' in path:
        return '민법'
    elif '형사' in path or '형법' in path:
        return '형법'
    elif '공법' in path or '헌법' in path or '행정법' in path:
        return '헌법'
    elif 'LEET' in path or '언어이해' in path or '추리논증' in path:
        return 'LEET'
    elif '자소서' in path or '입시' in path:
        return '입시'
    return '기타'

# Process files
results = {
    'to_rename': [],
    'skipped': [],
    'errors': []
}

type_counters = defaultdict(int)

for file_info in untyped_files:
    path = file_info['path']
    filename = file_info['filename']
    directory = file_info['dir']
    
    # Skip non-PDF/non-md files for now (except specific types)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ['.pdf', '.md', '.docx', '.hwp', '.gdoc']:
        results['skipped'].append({
            'path': path,
            'reason': f'Extension {ext} not supported for auto-typing'
        })
        continue
    
    # Already has type-like pattern
    if re.match(r'^\(\d+-\d+\)', filename):
        results['skipped'].append({
            'path': path,
            'reason': 'Already has type number'
        })
        continue
    
    # Determine type
    type_num = determine_type(file_info)
    subject = extract_subject(file_info)
    seq = get_next_sequence(type_counters, type_num, subject)
    
    # Create new filename
    new_filename = f"({type_num}-{seq:02d}){filename}"
    new_path = os.path.join(directory, new_filename)
    
    results['to_rename'].append({
        'original_path': path,
        'new_path': new_path,
        'original_name': filename,
        'new_name': new_filename,
        'type': type_num,
        'subject': subject
    })

# Save results
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# Summary by type
type_summary = defaultdict(int)
for item in results['to_rename']:
    type_summary[item['type']] += 1

print(f"=== 유형 분류 결과 ===")
print(f"이름 변경 대상: {len(results['to_rename'])}개")
print(f"건너뜀: {len(results['skipped'])}개")
print(f"\n유형별 분포:")
type_names = {1: '교재', 2: '정리', 3: '사례', 4: '선택', 5: '기타'}
for t in sorted(type_summary.keys()):
    print(f"  ({t}) {type_names[t]}: {type_summary[t]}개")
print(f"\n결과 파일: {output_file}")
