#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
파일 정리 스크립트 (Trash 로직 포함)
classification-rules.md 및 사용자 요청 반영
"""

import os
import shutil
import re
import sys
import datetime
from pathlib import Path

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 기본 디렉토리
BASE_DIR = Path(r"H:\내 드라이브")

# 타겟 디렉토리 (기존 분류 + Trash)
DIRS = {
    # Trash (임시 보관)
    "_trash/중복": BASE_DIR / "_trash" / "중복",
    "_trash/빈폴더": BASE_DIR / "_trash" / "빈폴더",
    "_trash/통합됨": BASE_DIR / "_trash" / "통합됨",
    "_trash/구버전": BASE_DIR / "_trash" / "구버전",
    "_trash/사용안함": BASE_DIR / "_trash" / "사용안함",

    # 변호사시험 과목
    "민사/진행중/교재": BASE_DIR / "민사" / "진행중" / "교재",
    "민사/참고자료": BASE_DIR / "민사" / "참고자료",
    "형사/보관": BASE_DIR / "형사" / "보관",
    "공법/보관": BASE_DIR / "공법" / "보관",
    "선택": BASE_DIR / "선택",

    # 로스쿨
    "로스쿨/LEET": BASE_DIR / "로스쿨" / "LEET",
    "로스쿨/입시": BASE_DIR / "로스쿨" / "입시",

    # 기타
    "성경": BASE_DIR / "성경",
    "기타/경제학": BASE_DIR / "기타" / "경제학",
    "기타": BASE_DIR / "기타",

    # 노트앱
    "_노트앱/GoodNotes": BASE_DIR / "_노트앱" / "GoodNotes",
    "_노트앱/Notability": BASE_DIR / "_노트앱" / "Notability",

    # 특수
    "_inbox": BASE_DIR / "_inbox",
    "_unrecognized": BASE_DIR / "_unrecognized",
    "_unrecognized/images": BASE_DIR / "_unrecognized" / "images",
    "_unclassified_images": BASE_DIR / "_unclassified_images",
    "_unclassified_videos": BASE_DIR / "_unclassified_videos",
}

# 분류 키워드 (reclassify.py 유지 + 구체화)
KEYWORDS = {
    "민사/진행중/교재": [
        "민법", "민소법", "민사소송법", "물권", "채권", "계약", "불법행위", "가족법", "친족", "상속",
        "송영곤", "박승수", "곽낙규", "윤동환", "김준호", "지원림", "민법의맥"
    ],
    "형사/보관": [
        "형법", "형소법", "형사소송법", "홍영기", "이주원", "김기용"
    ],
    "공법/보관": [
        "헌법", "행정법", "정인영", "전진명", "이재빈"
    ],
    "로스쿨/LEET": [
        "LEET", "리트", "언어이해", "추리논증", "논증", "PSAT", "양상논리"
    ],
    "로스쿨/입시": [
        "자소서", "자기소개서", "면접", "학업계획서", "지원동기", "입시", "로스쿨"
    ],
    "성경": [
        "성경", "기도", "말씀", "묵상", "교회", "창세기", "마태복음", "로마서"
    ],
    "기타/경제학": [
        "경제학", "미시경제", "거시경제", "맨큐", "이준구"
    ]
}

# 스킵할 디렉토리 (시스템 폴더 및 이미 분류된 폴더)
SKIP_DIRS = {
    BASE_DIR / ".agent",
    BASE_DIR / ".gemini",
    BASE_DIR / "_trash",  # Trash 폴더 자체는 건너뜀
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

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic'}
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv'}

def ensure_dirs():
    for d in DIRS.values():
        d.mkdir(parents=True, exist_ok=True)

def is_skip_dir(path: Path) -> bool:
    for skip in SKIP_DIRS:
        # 하위 디렉토리 포함 체크
        try:
            if path == skip or skip in path.parents:
                return True
        except:
            pass
    return False

def is_copy_file(filename: str) -> bool:
    """파일명이 복사본인지 확인"""
    copy_indicators = ["의 사본", " - Copy", "복사본", "(1)", " (1)", "(2)", " (2)"]
    # 확장자 제외하고 체크
    stem = Path(filename).stem
    
    # (숫자) 패턴은 파일명 끝에 오는 경우만
    if re.search(r'\(\d+\)$', stem):
        return True
        
    for ind in copy_indicators:
        if ind in stem:
            return True
    return False

def classify_file(filepath: Path) -> str:
    filename = filepath.name
    
    # 1. 명시적 복사본 체크 -> _trash/중복
    if is_copy_file(filename):
        return "_trash/중복"
        
    # 2. 확장자 및 특수 문자 체크
    if any(c in filename for c in ['', '□', '?']):
        return "_unrecognized"
        
    ext = filepath.suffix.lower()
    if ext in IMAGE_EXTS:
        return "_unclassified_images"
    if ext in VIDEO_EXTS:
        return "_unclassified_videos"
    if ext == '.goodnotes':
        return "_노트앱/GoodNotes"
    
    # 3. 키워드 매칭
    name_lower = filename.lower()
    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in name_lower:
                return category
                
    # 4. 기본값
    return "_inbox"

def move_to_trash(src_path: Path, reason_subdir: str):
    """파일을 Trash의 특정 사유 폴더로 이동"""
    target_dir = DIRS.get(f"_trash/{reason_subdir}")
    if not target_dir:
        target_dir = BASE_DIR / "_trash" / reason_subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        
    dst_path = target_dir / src_path.name
    
    # Trash 내 이름 충돌 시 타임스탬프 추가
    if dst_path.exists():
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dst_path = target_dir / f"{src_path.stem}_{timestamp}{src_path.suffix}"
        
    try:
        shutil.move(str(src_path), str(dst_path))
        print(f"TRASH [{reason_subdir}]: {src_path.name}")
    except Exception as e:
        print(f"Error moving to trash {src_path.name}: {e}")

def move_file(src_path: Path, category: str):
    target_dir = DIRS.get(category)
    if not target_dir:
        # 매핑에 없으면 _inbox로 (안전을 위해)
        target_dir = BASE_DIR / "_inbox"
    
    dst_path = target_dir / src_path.name
    
    # 대상 경로에 이미 파일이 존재하면 -> 중복 취급하여 Trash로 이동
    if dst_path.exists() and src_path != dst_path:
        print(f"DUPLICATE DETECTED during move: {src_path.name} existing in {category}")
        move_to_trash(src_path, "중복")
        return

    try:
        shutil.move(str(src_path), str(dst_path))
        print(f"MOVED: {src_path.name} -> {category}")
    except Exception as e:
        print(f"Error moving {src_path.name}: {e}")

def main():
    print("=== 파일 정리 (Trash 로직 적용) 시작 ===")
    ensure_dirs()
    
    # 1. 루트 및 Inbox 파일 정리
    targets = [BASE_DIR, BASE_DIR / "_inbox"]
    
    total_moved = 0
    
    for target_dir in targets:
        if not target_dir.exists():
            continue
            
        print(f"\nScanning {target_dir}...")
        
        # 파일 목록 순회 (디렉토리 제외)
        for item in target_dir.iterdir():
            if item.is_dir():
                continue
            if is_skip_dir(item):
                continue
            if item.name.startswith('.'): # 숨김 파일 스킵
                continue
                
            category = classify_file(item)
            
            # _inbox에 있는 파일이 category가 _inbox라면 이동 안함
            if category == "_inbox" and target_dir == BASE_DIR / "_inbox":
                continue
            
            # Trash 카테고리면 trash 이동 함수 사용
            if category.startswith("_trash/"):
                reason = category.split("/")[1]
                move_to_trash(item, reason)
            else:
                move_file(item, category)
            
            total_moved += 1
            
    print(f"\n총 {total_moved}개 파일 처리됨.")
    print("완료.")

if __name__ == "__main__":
    main()
