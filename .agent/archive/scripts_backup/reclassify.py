#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
파일 재분류 스크립트
classification-rules.md 기반
"""

import os
import shutil
import re
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Base directory
BASE_DIR = Path(r"H:\내 드라이브")

# Target Directories
DIRS = {
    # 변호사시험 과목 (메인)
    "민사": BASE_DIR / "민사",
    "형사": BASE_DIR / "형사",
    "공법": BASE_DIR / "공법",
    "선택": BASE_DIR / "선택",
    # 민사 하위 (진행중)
    "민사/교재": BASE_DIR / "민사" / "진행중" / "교재",
    "민사/전사문": BASE_DIR / "민사" / "진행중" / "전사문",
    "민사/필기": BASE_DIR / "민사" / "진행중" / "필기",
    "민사/기타자료": BASE_DIR / "민사" / "진행중" / "기타자료",
    # 로스쿨
    "로스쿨/LEET": BASE_DIR / "로스쿨" / "LEET",
    "로스쿨/입시": BASE_DIR / "로스쿨" / "입시",
    # 기타
    "성경": BASE_DIR / "성경",
    "기타": BASE_DIR / "기타",
    # 노트앱
    "_노트앱/GoodNotes": BASE_DIR / "_노트앱" / "GoodNotes",
    "_노트앱/Notability": BASE_DIR / "_노트앱" / "Notability",
    # 특수
    "_inbox": BASE_DIR / "_inbox",
    "_unrecognized/images": BASE_DIR / "_unrecognized" / "images",
    "_unrecognized/others": BASE_DIR / "_unrecognized" / "others",
    "_unclassified_images": BASE_DIR / "_unclassified_images",
    "_unclassified_videos": BASE_DIR / "_unclassified_videos",
}

# Keywords for classification
KEYWORDS = {
    "민사": [
        "민법", "민소법", "민사소송법", "물권", "채권", "계약", "불법행위", 
        "가족법", "친족", "상속", "등기", "담보", "저당", "질권",
        "송영곤", "박승수", "곽낙규", "윤동환", "김준호", "지원림",
        "민법입문", "민법사례", "민사법", "재산법"
    ],
    "형사": [
        "형법", "형소법", "형사소송법", "범죄론", "형벌론", "구성요건", 
        "위법성", "책임", "공범", "미수", "정당방위",
        "홍영기", "이주원", "김기용", "오영근", "이재상",
        "형법각론", "형법총론", "형각", "형총"
    ],
    "공법": [
        "헌법", "행정법", "기본권", "통치구조", "행정작용", "행정구제",
        "위헌심사", "권력분립", "지방자치", "공권력",
        "정인영", "전진명", "이재빈", "정종섭", "김하열"
    ],
    "선택": [
        "국제법", "노동법", "조세법", "환경법", "지재권", "국제거래법",
        "특허", "저작권", "상표", "세법"
    ],
    "로스쿨/LEET": [
        "LEET", "리트", "언어이해", "추리논증", "논리", "양상논리", 
        "형식논리", "논증", "PSAT", "언어논리", "명제", "추론",
        "논리학", "연역", "귀납"
    ],
    "로스쿨/입시": [
        "자소서", "자기소개서", "면접", "학업계획서", "지원동기", "입시",
        "경희대", "고려대", "성균관대", "연세대", "한양대", "서울대", 
        "이화여대", "서강대", "중앙대", "법학전문대학원", "증명사진"
    ],
    "성경": [
        "성경", "기도", "말씀", "묵상", "교회", "목회", "복음", "설교", "QT",
        "코람데오", "호튼", "하이델베르크", "신학", "예수", "하나님",
        "창세기", "출애굽기", "마태복음", "로마서"
    ]
}

# 내부 분류 키워드 (민사/형사/공법 하위 분류용)
CATEGORY_KEYWORDS = {
    "교재": ["논점", "사례연습", "진도표", "주요쟁점", "강의자료", "기본강의-", "집행법", "샘플", "강의계획서", "민법의맥", "형법총론"],
    "전사문": ["_raw.md", "_processed.md", "전사문", "_trs"],
    "필기": ["필기노트", "모의시험", "채점평", "요약", "정리", "DT-선택형", "선택형자료", "주요사례"],
    "참고자료": ["등기부", "조문", "판례집", "법전"],
    "기타자료": ["안내문", "공지사항", "일정표", "안내", "공지"],
}

# Directories to skip
SKIP_DIRS = {
    BASE_DIR / ".agent",
    BASE_DIR / ".gemini",
    BASE_DIR / "System Volume Information",
    BASE_DIR / "$RECYCLE.BIN",
    BASE_DIR / "_inbox",
    BASE_DIR / "_unrecognized",
    BASE_DIR / "_unclassified_images",
    BASE_DIR / "_unclassified_videos",
    BASE_DIR / "_노트앱",
    BASE_DIR / "민사",
    BASE_DIR / "형사",
    BASE_DIR / "공법",
    BASE_DIR / "선택",
    BASE_DIR / "로스쿨",
    BASE_DIR / "성경",
    BASE_DIR / "기타",
}

# Image extensions
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.tiff'}
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.m4v'}

def ensure_dirs():
    """Create all target directories"""
    for d in DIRS.values():
        d.mkdir(parents=True, exist_ok=True)

def is_skip_dir(path: Path) -> bool:
    """Check if path should be skipped"""
    for skip in SKIP_DIRS:
        try:
            path.relative_to(skip)
            return True
        except ValueError:
            pass
    return False

def is_unrecognized(filename: str) -> bool:
    """Check if filename contains unrecognized characters"""
    # Check for broken characters
    if any(c in filename for c in ['�', '□', '?']):
        return True
    # Check for only whitespace or extension
    name = Path(filename).stem
    if not name or name.isspace():
        return True
    return False

def classify_by_extension(filename: str) -> str | None:
    """Classify by file extension"""
    ext = Path(filename).suffix.lower()
    
    # Note apps
    if ext == '.goodnotes':
        return "_노트앱/GoodNotes"
    if ext == '.note':
        return "_노트앱/Notability"
    
    # Media
    if ext in IMAGE_EXTS:
        return "_unclassified_images"
    if ext in VIDEO_EXTS:
        return "_unclassified_videos"
    
    return None

def classify_by_keyword(filename: str) -> str | None:
    """Classify by keyword matching"""
    name_lower = filename.lower()
    
    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in name_lower:
                return category
    
    return None

def classify_file(filepath: Path) -> str | None:
    """Main classification logic"""
    filename = filepath.name
    
    # 1. Check unrecognized
    if is_unrecognized(filename):
        ext = filepath.suffix.lower()
        if ext in IMAGE_EXTS:
            return "_unrecognized/images"
        return "_unrecognized/others"
    
    # 2. Check extension-based
    ext_category = classify_by_extension(filename)
    if ext_category:
        return ext_category
    
    # 3. Check keyword-based
    keyword_category = classify_by_keyword(filename)
    if keyword_category:
        return keyword_category
    
    # 4. No match -> inbox
    return "_inbox"

def move_file(src_path: Path, category: str):
    """Move file to target directory"""
    target_dir = DIRS.get(category)
    if not target_dir:
        print(f"Unknown category: {category}")
        return
    
    dst_path = target_dir / src_path.name
    
    if src_path == dst_path:
        return
    
    # Handle duplicates
    if dst_path.exists():
        stem = src_path.stem
        suffix = src_path.suffix
        count = 1
        while dst_path.exists():
            dst_path = target_dir / f"{stem}_{count}{suffix}"
            count += 1
    
    try:
        shutil.move(str(src_path), str(dst_path))
        print(f"Moved: {src_path.name} -> {category}")
    except Exception as e:
        print(f"Error moving {src_path.name}: {e}")

def clean_empty_dirs(path: Path):
    """Remove empty directories"""
    for root, dirs, files in os.walk(str(path), topdown=False):
        root_path = Path(root)
        if is_skip_dir(root_path):
            continue
        
        for name in dirs:
            d_path = root_path / name
            if is_skip_dir(d_path):
                continue
            try:
                if not any(d_path.iterdir()):
                    d_path.rmdir()
                    print(f"Removed empty dir: {d_path}")
            except Exception as e:
                print(f"Error removing {d_path}: {e}")

def main():
    print("=== 파일 분류 시작 ===")
    print(f"Base: {BASE_DIR}")
    
    # Create directories
    ensure_dirs()
    print("대상 폴더 생성 완료")
    
    # Collect and classify
    moved_count = 0
    for root, dirs, files in os.walk(str(BASE_DIR)):
        root_path = Path(root)
        
        if is_skip_dir(root_path):
            continue
        
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.startswith('.'):
                continue
            
            src_path = root_path / file
            category = classify_file(src_path)
            
            if category:
                move_file(src_path, category)
                moved_count += 1
    
    print(f"\n분류 완료: {moved_count} 파일 이동")
    
    # Cleanup
    print("\n빈 폴더 정리 중...")
    clean_empty_dirs(BASE_DIR)
    
    print("\n=== 완료 ===")

if __name__ == "__main__":
    main()
