#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
내부 분류 스크립트 v2
- 파일명 + 내용에서 강사/교재명 추출
- 추출 불가 시 알림
"""

import os
import sys
import re
from pathlib import Path
from typing import Optional, Tuple

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# PDF 텍스트 추출 시도
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    print("[경고] PyMuPDF 없음 - PDF 내용 분석 불가. pip install pymupdf")

BASE_DIR = Path(r"H:\내 드라이브")

# 강사명 키워드
INSTRUCTORS = {
    "송영곤": ["송영곤", "송쌤", "송선생", "민법입문", "민사법사례연습"],
    "윤동환": ["윤동환", "민법의맥", "민법 사례의 맥", "사례의맥"],
    "곽낙규": ["곽낙규", "곽쌤", "민법사례연습"],
    "박승수": ["박승수", "민법기본사례"],
    "김준호": ["김준호"],
    "홍영기": ["홍영기", "형법 총론", "형사법"],
    "이주원": ["이주원"],
    "김기용": ["김기용"],
    "정인영": ["정인영", "헌법"],
    "전진명": ["전진명", "행정법", "파이널"],
    "이재빈": ["이재빈"],
}

# 교재명 키워드
TEXTBOOKS = {
    "민법의맥": ["민법의맥", "민법의 맥"],
    "논점민법강의": ["논점민법", "논점 민법"],
    "민법사례연습": ["민법사례연습", "사례연습"],
    "민법기본사례": ["민법기본사례", "기본사례"],
    "민사법사례연습": ["민사법사례연습", "민사법 사례"],
    "형법총론": ["형법총론", "형법 총론"],
    "헌법": ["헌법"],
    "행정법": ["행정법"],
}

# 과목 분류 키워드
SUBJECT_KEYWORDS = {
    "민사": ["민법", "민사", "물권", "채권", "계약", "불법행위", "가족법", "친족", "상속"],
    "형사": ["형법", "형사", "범죄론", "형벌론", "구성요건", "위법성", "책임"],
    "공법": ["헌법", "행정법", "기본권", "통치구조", "행정작용", "행정구제"],
}

# 내부 분류 키워드 (교재/전사문/필기/기타자료)
CATEGORY_KEYWORDS = {
    "교재": ["논점", "사례연습", "진도표", "주요쟁점", "강의자료", "기본강의-", "집행법", "샘플", "강의계획서", "민법의맥", "형법총론"],
    "전사문": ["_raw.md", "_processed.md", "전사문", "_trs"],
    "필기": ["필기노트", "모의시험", "채점평", "요약", "정리", "DT-선택형", "선택형자료", "주요사례"],
    "참고자료": ["등기부", "조문", "판례집", "법전"],
    "기타자료": ["안내문", "공지사항", "일정표", "안내", "공지"],
}


def extract_text_from_pdf(file_path: Path, max_pages: int = 3) -> str:
    """PDF 첫 N페이지에서 텍스트 추출"""
    if not HAS_PYMUPDF:
        return ""
    
    try:
        doc = fitz.open(str(file_path))
        text = ""
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            text += page.get_text()
        doc.close()
        return text[:5000]  # 최대 5000자
    except Exception as e:
        return ""


def detect_instructor(text: str) -> Optional[str]:
    """텍스트에서 강사명 감지"""
    text_lower = text.lower()
    
    for instructor, keywords in INSTRUCTORS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return instructor
    return None


def detect_textbook(text: str) -> Optional[str]:
    """텍스트에서 교재명 감지"""
    text_lower = text.lower()
    
    for textbook, keywords in TEXTBOOKS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return textbook
    return None


def detect_subject(text: str) -> Optional[str]:
    """텍스트에서 과목 감지"""
    text_lower = text.lower()
    
    for subject, keywords in SUBJECT_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        if matches >= 2:
            return subject
    return None


def detect_category(text: str) -> str:
    """텍스트에서 내부 분류 감지"""
    text_lower = text.lower()
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return category
    return "기타자료"  # 기본값 (교재/전사문/필기에 해당 안될 경우)


def analyze_file(file_path: Path) -> dict:
    """파일 분석 - 파일명 + 내용에서 정보 추출"""
    result = {
        "filename": file_path.name,
        "instructor": None,
        "textbook": None,
        "subject": None,
        "category": None,
        "source": "filename",  # 정보 출처: filename 또는 content
        "confidence": "low",
    }
    
    # 1. 파일명에서 추출 시도
    filename_text = file_path.stem.replace("_", " ")
    
    result["instructor"] = detect_instructor(filename_text)
    result["textbook"] = detect_textbook(filename_text)
    result["subject"] = detect_subject(filename_text)
    result["category"] = detect_category(filename_text)
    
    if result["instructor"] or result["textbook"]:
        result["confidence"] = "high"
        return result
    
    # 2. 파일 내용에서 추출 시도 (PDF만)
    if file_path.suffix.lower() == '.pdf' and HAS_PYMUPDF:
        content = extract_text_from_pdf(file_path)
        if content:
            result["source"] = "content"
            
            detected_instructor = detect_instructor(content)
            detected_textbook = detect_textbook(content)
            detected_subject = detect_subject(content)
            
            if detected_instructor:
                result["instructor"] = detected_instructor
                result["confidence"] = "medium"
            if detected_textbook:
                result["textbook"] = detected_textbook
                result["confidence"] = "medium"
            if detected_subject and not result["subject"]:
                result["subject"] = detected_subject
    
    # 3. 추출 불가 시 표시
    if not result["instructor"] and not result["textbook"]:
        result["confidence"] = "unknown"
    
    return result


def generate_new_filename(file_path: Path, analysis: dict) -> str:
    """분석 결과 기반 새 파일명 생성"""
    parts = []
    
    # 과목_강사_제목 형식
    if analysis["subject"]:
        parts.append(analysis["subject"])
    
    if analysis["instructor"]:
        parts.append(analysis["instructor"])
    elif analysis["textbook"]:
        parts.append(analysis["textbook"])
    
    # 기존 파일명에서 유의미한 부분 추출
    stem = file_path.stem
    # 기존 접두어 제거 (민법_, 형법_ 등)
    for subject in SUBJECT_KEYWORDS.keys():
        if stem.startswith(f"{subject}_"):
            stem = stem[len(subject)+1:]
            break
    
    if stem:
        parts.append(stem)
    
    new_name = "_".join(parts) + file_path.suffix
    # 파일명 정리 (공백→언더스코어, 중복 언더스코어 제거)
    new_name = re.sub(r'\s+', '_', new_name)
    new_name = re.sub(r'_+', '_', new_name)
    
    return new_name


def main():
    print("=== 파일 분석 및 분류 ===\n")
    
    if not HAS_PYMUPDF:
        print("[경고] PDF 내용 분석을 위해 설치 필요: pip install pymupdf\n")
    
    # 테스트: 민사 폴더 분석
    test_dir = BASE_DIR / "민사" / "진행중"
    
    unknown_files = []
    
    for subdir in ["교재", "전사문", "필기", "기타자료"]:
        folder = test_dir / subdir
        if not folder.exists():
            continue
        
        print(f"\n--- {subdir} ---")
        for file_path in folder.iterdir():
            if not file_path.is_file():
                continue
            
            analysis = analyze_file(file_path)
            
            if analysis["confidence"] == "unknown":
                unknown_files.append(file_path)
                print(f"[?] {file_path.name}")
            else:
                instructor = analysis["instructor"] or "?"
                textbook = analysis["textbook"] or ""
                source = analysis["source"]
                print(f"[{source[0].upper()}] {file_path.name} -> {instructor} / {textbook}")
    
    if unknown_files:
        print(f"\n=== 추출 불가 파일 ({len(unknown_files)}개) ===")
        for f in unknown_files:
            print(f"  - {f.name}")


if __name__ == "__main__":
    main()
