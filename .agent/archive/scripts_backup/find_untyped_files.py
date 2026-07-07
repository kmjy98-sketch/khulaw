# -*- coding: utf-8 -*-
"""
유형번호가 없는 파일 찾기
유형번호 패턴: (1-01), (2-03), (3-02) 등
"""
import os
import re
import json

root_path = r"H:\내 드라이브"
output_file = os.path.join(root_path, ".agent", "untyped_files.json")

# 유형번호 패턴: (숫자-숫자) 로 시작
type_pattern = re.compile(r'^\(\d+-\d+\)')

# 분류 대상 폴더들 (법학 교재/자료 폴더)
target_folders = [
    os.path.join(root_path, "민사"),
    os.path.join(root_path, "형사"),
    os.path.join(root_path, "공법"),
    os.path.join(root_path, "로스쿨"),
]

# 제외 폴더
exclude_patterns = ['.agent', '_trash', '_inbox', '_노트앱', '기타', '성경']

def should_skip(path):
    for pattern in exclude_patterns:
        if pattern in path:
            return True
    return False

# 유형번호 없는 파일 찾기
untyped_files = []

for target_folder in target_folders:
    if not os.path.exists(target_folder):
        continue
    for dirpath, dirnames, filenames in os.walk(target_folder):
        # 제외 폴더 스킵
        if should_skip(dirpath):
            continue
        
        for filename in filenames:
            # 유형번호가 없는 파일
            if not type_pattern.match(filename):
                full_path = os.path.join(dirpath, filename)
                untyped_files.append({
                    'path': full_path,
                    'dir': dirpath,
                    'filename': filename
                })

# 루트 폴더의 PDF 파일도 확인 (법학 관련)
for filename in os.listdir(root_path):
    full_path = os.path.join(root_path, filename)
    if os.path.isfile(full_path) and filename.endswith('.pdf'):
        if not type_pattern.match(filename):
            # 법학/LEET 관련 키워드 확인
            keywords = ['민법', '형법', '헌법', '행정법', 'LEET', '자소서', '로스쿨', 
                       '언어이해', '추리논증', '송영곤', '윤동환', '박승수', '곽낙규',
                       '모의고사', '기출', '해설', '문제']
            if any(kw in filename for kw in keywords):
                untyped_files.append({
                    'path': full_path,
                    'dir': root_path,
                    'filename': filename
                })

# 저장
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(untyped_files, f, ensure_ascii=False, indent=2)

print(f"유형번호 없는 파일: {len(untyped_files)}개")
print(f"저장 위치: {output_file}")

# 폴더별 분류
by_folder = {}
for f in untyped_files:
    folder = os.path.basename(f['dir'])
    if folder not in by_folder:
        by_folder[folder] = 0
    by_folder[folder] += 1

print("\n폴더별 분포:")
for folder, count in sorted(by_folder.items(), key=lambda x: -x[1]):
    print(f"  {folder}: {count}개")
