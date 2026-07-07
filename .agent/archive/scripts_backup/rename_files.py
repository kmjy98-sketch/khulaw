#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
파일명 표준화 스크립트
형식: 과목_강사_파일명
"""

import os
import re
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(r"H:\내 드라이브")

# Subject detection
SUBJECT_MAP = {
    "민사": {
        "folder": "민사",
        "keywords": ["민법", "민소법", "물권", "채권", "계약", "민총", "민사"],
        "code": "민법"
    },
    "형사": {
        "folder": "형사", 
        "keywords": ["형법", "형소법", "형총", "형각", "범죄"],
        "code": "형법"
    },
    "공법": {
        "folder": "공법",
        "keywords": ["헌법", "행정법", "기본권", "통치"],
        "code": "헌법"
    }
}

# Instructor patterns
INSTRUCTORS = {
    # 민사
    "송영곤": ["송영곤", "논점민법", "민법입문"],
    "윤동환": ["윤동환", "민법의맥", "민맥", "사례의맥"],
    "박승수": ["박승수", "민법기본사례"],
    "곽낙규": ["곽낙규", "변사기"],
    # 형사
    "홍영기": ["홍영기"],
    "홍형철": ["홍형철"],
    "이주원": ["이주원"],
    "김기용": ["김기용", "COMPACT"],
    # 공법
    "전진명": ["전진명"],
    "이재빈": ["이재빈"],
    "정인영": ["정인영"],
}

def detect_subject(filename: str, folder: str) -> str:
    """Detect subject from filename or folder"""
    # From folder
    for subj, info in SUBJECT_MAP.items():
        if info["folder"] in folder:
            return info["code"]
    
    # From filename
    fl = filename.lower()
    for subj, info in SUBJECT_MAP.items():
        for kw in info["keywords"]:
            if kw.lower() in fl:
                return info["code"]
    
    return ""

def detect_instructor(filename: str) -> str:
    """Detect instructor from filename"""
    for instr, patterns in INSTRUCTORS.items():
        for pat in patterns:
            if pat.lower() in filename.lower():
                return instr
    return ""

def clean_filename(name: str) -> str:
    """Clean up filename"""
    # Remove common prefixes
    name = re.sub(r'^\(\d+\)\[.*?\]\s*', '', name)
    name = re.sub(r'^\[\d+\]\s*', '', name)
    name = re.sub(r'^\d{4}\.\s*\d{2}\.\s*', '', name)  # 2023. 02.
    name = re.sub(r'^\d{2,4}\s+', '', name)  # 24 or 2024
    
    # Remove instructor name if already detected
    for instr in INSTRUCTORS.keys():
        name = name.replace(instr, '').replace(f"{instr}t", '').replace(f"{instr}T", '')
    
    # Remove "변호사" etc
    name = name.replace("변호사", "").replace("선생님", "")
    
    # Clean up spaces and underscores
    name = re.sub(r'_+', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = name.strip('_').strip()
    
    return name

def standardize_filename(filepath: Path, folder: str) -> str:
    """Generate standardized filename"""
    original = filepath.stem
    ext = filepath.suffix
    
    subject = detect_subject(original, folder)
    instructor = detect_instructor(original)
    
    # If no subject/instructor detected, return original
    if not subject and not instructor:
        return None  # Will need manual/PDF check
    
    # Clean the original name
    cleaned = clean_filename(original)
    
    # Build new name
    parts = []
    if subject:
        parts.append(subject)
    if instructor:
        parts.append(instructor)
    if cleaned:
        parts.append(cleaned)
    
    if len(parts) < 2:
        return None
    
    new_name = "_".join(parts) + ext
    return new_name

def rename_files_in_folder(folder_path: Path, dry_run: bool = True):
    """Rename files in a folder"""
    renamed = 0
    skipped = []
    
    for item in folder_path.rglob("*"):
        if not item.is_file():
            continue
        if item.suffix.lower() not in ['.pdf', '.md', '.docx', '.gdoc']:
            continue
        
        folder_str = str(item.parent)
        new_name = standardize_filename(item, folder_str)
        
        if new_name is None:
            skipped.append(item.name)
            continue
        
        if new_name == item.name:
            continue
        
        new_path = item.parent / new_name
        
        # Handle duplicates
        if new_path.exists():
            stem = Path(new_name).stem
            ext = Path(new_name).suffix
            count = 1
            while new_path.exists():
                new_path = item.parent / f"{stem}_{count}{ext}"
                count += 1
        
        if dry_run:
            print(f"RENAME: {item.name}")
            print(f"    -> {new_path.name}")
        else:
            item.rename(new_path)
            print(f"RENAMED: {item.name} -> {new_path.name}")
        
        renamed += 1
    
    return renamed, skipped

def main():
    print("=== 파일명 표준화 (DRY RUN) ===")
    print("과목_강사_파일명 형식으로 변환")
    print()
    
    total_renamed = 0
    all_skipped = []
    
    for subject in ["민사", "형사", "공법"]:
        folder = BASE_DIR / subject / "active"
        if folder.exists():
            print(f"\n--- {subject} ---")
            renamed, skipped = rename_files_in_folder(folder, dry_run=False)
            total_renamed += renamed
            all_skipped.extend(skipped)
    
    print(f"\n=== 요약 ===")
    print(f"변환 예정: {total_renamed}개")
    print(f"인식 불가(수동 확인 필요): {len(all_skipped)}개")
    
    if all_skipped:
        print("\n인식 불가 파일:")
        for f in all_skipped[:20]:
            print(f"  - {f}")
        if len(all_skipped) > 20:
            print(f"  ... 외 {len(all_skipped) - 20}개")

if __name__ == "__main__":
    main()
