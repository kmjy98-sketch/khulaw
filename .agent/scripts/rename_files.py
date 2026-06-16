"""
파일명 교정 스크립트 v2
기존: 유형번호-순서_과목_강사_강의명_세부항목명_년도
새로: 책이름_분야_연도 (유형별 폴더 이동, 동일 책이름 중복 시 저자_책이름_분야_연도)
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

# 설정
ROOT = Path(r"H:\내 드라이브")
DRY_RUN = False  # True면 미리보기만, False면 실제 실행

# 대상 폴더
TARGET_DIRS = [
    # 민사
    ROOT / "민사" / "진행중" / "교재",
    ROOT / "민사" / "보관",
    ROOT / "민사",
    ROOT / "민사" / "진행중",
    # 형사
    ROOT / "형사" / "보관",
    ROOT / "형사" / "보관" / "교재",
    ROOT / "형사" / "진행중" / "교재",
    ROOT / "형사",
    # 공법
    ROOT / "공법" / "보관",
    ROOT / "공법" / "보관" / "교재",
    ROOT / "공법" / "진행중" / "교재",
    ROOT / "공법",
]

# 유형별 대상 폴더
TYPE_FOLDERS = {
    "1": "교재",
    "2": "정리", 
    "3": "사례",
    "4": "선택형",
    "5": "기타",
}

# 강의명 약어 확장
LECTURE_MAP = {
    "기본민강": "기본강의",
    "기본민법강의": "기본강의",
    "민사법사례연습": "사례연습",
    "민법사례연습": "사례연습",
}
# 동일 책이름 중복 → 저자 포함 대상
# 표지 확인 결과 현재 모든 책이름 고유 (민법1은 폴더명이지 책이름이 아님)
DUPLICATE_BOOKS = set()

def parse_old_filename(filename: str) -> dict | None:
    """기존 파일명 파싱"""
    # 확장자 분리
    name, ext = os.path.splitext(filename)
    ext = ext.lstrip('.')
    
    # 패턴: N-NN_과목_저자_강의명_세부...
    match = re.match(r'^(\d)-(\d{1,2})_(.+)$', name)
    if not match:
        return None
    
    type_num, seq, rest = match.groups()
    
    # 나머지 부분을 언더스코어로 분리
    parts = rest.split('_')
    
    if len(parts) < 2:
        return None
    
    subject = parts[0]  # 과목
    author = parts[1] if len(parts) > 1 else None
    lecture = parts[2] if len(parts) > 2 else None
    detail_parts = parts[3:] if len(parts) > 3 else []
    detail = '_'.join(detail_parts)
    
    # 연도 추출 (26), (25), (24), (23) 등
    year = None
    year_match = re.search(r'\((\d{2})\)', detail)
    if year_match:
        year = year_match.group(1)
        detail = re.sub(r'\(\d{2}\)', '', detail).strip('_- ')
    
    # 날짜 형식에서 연도 추출 (24.12.16. 등)
    if not year:
        date_match = re.search(r'-?(\d{2})\.\d{1,2}\.\d{1,2}\.?', detail)
        if date_match:
            year = date_match.group(1)
            detail = re.sub(r'-?\d{2}\.\d{1,2}\.\d{1,2}\.?', '', detail).strip('_- ')
    
    return {
        "type": type_num,
        "seq": seq,
        "subject": subject,
        "author": author if author and author != "26대비" else None,
        "lecture": lecture,
        "detail": detail,
        "year": year,
        "ext": ext,
    }

def clean_detail(detail: str, keep_number: bool = True) -> str:
    """detail 정리"""
    if not detail:
        return ""
    
    # (사례), (선택), (정리), (교재) 등 제거
    detail = re.sub(r'\((사례|선택|정리|교재|기타)\)', '', detail)
    
    # 날짜 형식 제거
    detail = re.sub(r'-?\d{2}\.\d{1,2}\.\d{1,2}\.?', '', detail)
    
    # 괄호와 내용 제거
    detail = re.sub(r'\([^)]*\)', '', detail)
    
    # 하이픈을 언더스코어로
    detail = detail.replace('-', '_')
    
    # 연속 언더스코어 정리
    detail = re.sub(r'_+', '_', detail)
    
    return detail.strip('_- ')

def generate_new_filename(parsed: dict) -> str:
    """새 파일명 생성: 책이름_분야_연도 (동일 책이름 중복 시 저자_책이름_분야_연도)"""
    parts = []
    
    # 책이름 (강의명에서 약어 확장)
    lecture = parsed["lecture"] or parsed["subject"] or ""
    lecture = LECTURE_MAP.get(lecture, lecture)
    # 26기본강의 → 기본강의
    lecture = re.sub(r'^\d{2}', '', lecture)
    
    # 동일 책이름 중복 시에만 저자 포함
    if lecture in DUPLICATE_BOOKS and parsed["author"]:
        parts.append(parsed["author"])
    
    if lecture:
        parts.append(lecture)
    
    # 분야 (detail에서 추출, 차수 포함)
    detail = clean_detail(parsed["detail"], keep_number=True)
    if detail:
        parts.append(detail)
    
    # 연도
    if parsed["year"]:
        parts.append(parsed["year"])
    
    new_name = "_".join(parts)
    
    # 특수문자 정리
    new_name = re.sub(r'[,\.\s]+', '_', new_name)
    new_name = re.sub(r'_+', '_', new_name)
    new_name = new_name.strip('_')
    
    # 확장자 추가 (점 포함!)
    new_name = f"{new_name}.{parsed['ext']}"
    
    return new_name

def get_target_folder(parsed: dict, current_dir: Path) -> Path:
    """유형에 따른 대상 폴더 결정 (과목별로 분기)"""
    type_folder = TYPE_FOLDERS.get(parsed["type"], "기타")
    
    # 과목별 기본 폴더 결정
    subject = parsed["subject"]
    if subject in ["민법", "민소법", "민사소송법"]:
        base = ROOT / "민사" / "진행중"
    elif subject in ["형법", "형소법", "형사소송법"]:
        base = ROOT / "형사" / "진행중"
    elif subject in ["헌법", "행정법"]:
        base = ROOT / "공법" / "진행중"
    else:
        # 기타 과목은 현재 폴더의 상위 구조 유지
        for parent in ["민사", "형사", "공법"]:
            if parent in str(current_dir):
                base = ROOT / parent / "진행중"
                break
        else:
            base = ROOT / "민사" / "진행중"  # 기본값
    
    return base / type_folder

def process_files():
    """파일 처리"""
    results = []
    seen_names = {}  # 중복 체크
    
    for target_dir in TARGET_DIRS:
        if not target_dir.exists():
            continue
            
        for file_path in target_dir.iterdir():
            if file_path.is_dir():
                continue
            
            filename = file_path.name
            parsed = parse_old_filename(filename)
            
            if not parsed:
                continue
            
            new_name = generate_new_filename(parsed)
            target_folder = get_target_folder(parsed, target_dir)
            
            # 중복 체크 및 해결
            full_new_name = new_name
            if new_name in seen_names:
                # 순서 번호 추가
                base, ext = os.path.splitext(new_name)
                counter = seen_names[new_name] + 1
                full_new_name = f"{base}_{counter}{ext}"
                seen_names[new_name] = counter
            else:
                seen_names[new_name] = 1
            
            new_path = target_folder / full_new_name
            
            result = {
                "old_path": str(file_path),
                "new_path": str(new_path),
                "old_name": filename,
                "new_name": full_new_name,
            }
            results.append(result)
            
            if DRY_RUN:
                status = "[중복]" if full_new_name != new_name else "[OK]"
                print(f"{status} {filename}")
                print(f"  →  {full_new_name}")
                print(f"  폴더: {target_folder.name}/")
                print()
            else:
                target_folder.mkdir(parents=True, exist_ok=True)
                file_path.rename(new_path)
                print(f"[완료] {filename} → {full_new_name}")
    
    return results

def main():
    print("=" * 60)
    print("파일명 교정 스크립트 v2")
    print(f"모드: {'DRY-RUN (미리보기)' if DRY_RUN else '실제 실행'}")
    print("=" * 60)
    print()
    
    results = process_files()
    
    print("=" * 60)
    print(f"총 {len(results)}개 파일 처리 {'예정' if DRY_RUN else '완료'}")
    print("=" * 60)
    
    # 로그 저장
    log_path = ROOT / ".agent" / "temp" / f"rename_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"로그 저장: {log_path}")
    
    return results

if __name__ == "__main__":
    main()
