#!/usr/bin/env python3
"""
Auto-Index: 마크다운에서 조문/판례/키워드 추출하여 tag_index.json 업데이트
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

# 인덱스 파일 경로
INDEX_PATH = Path(__file__).parent.parent.parent.parent / "state" / "tag_index.json"

# 추출 패턴
PATTERNS = {
    "articles": [
        r"제(\d+)조",  # 제126조
        r"민법\s*제?(\d+)조",  # 민법 제126조
    ],
    "cases": [
        r"대법원\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})",  # 대법원 2007.5.17
        r"(\d{2,4}다\d+)",  # 2018다40231
        r"전원합의체",  # 전원합의체 판례
    ],
    "keywords": [
        r"\*\*([가-힣]{2,10})\*\*",  # **볼드** 키워드
    ],
    "headers": [
        r"##\s*\d+\.\s*(.+?)(?:\s*\(페이지|\s*$)",  # ## 1. 제목 (페이지 X)
    ],
}


def load_index() -> dict:
    """기존 인덱스 로드"""
    if INDEX_PATH.exists():
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "version": "2.0",
        "last_updated": str(date.today()),
        "sources": {},
        "articles": {},
        "keywords": {},
    }


def save_index(index: dict) -> None:
    """인덱스 저장"""
    index["last_updated"] = str(date.today())
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=4)


def extract_from_file(filepath: Path) -> dict:
    """파일에서 조문/판례/키워드 추출"""
    content = filepath.read_text(encoding="utf-8")
    
    result = {
        "articles": set(),
        "keywords": set(),
        "cases": set(),
    }
    
    # 조문 추출
    for pattern in PATTERNS["articles"]:
        for match in re.finditer(pattern, content):
            article = f"{match.group(1)}조"
            result["articles"].add(article)
    
    # 판례 추출
    for pattern in PATTERNS["cases"]:
        for match in re.finditer(pattern, content):
            if "전원합의체" in pattern:
                result["cases"].add("전원합의체")
            else:
                result["cases"].add(match.group(0))
    
    # 키워드 추출 (볼드)
    for pattern in PATTERNS["keywords"]:
        for match in re.finditer(pattern, content):
            keyword = match.group(1)
            # 필터링: 일반적인 단어 제외
            if len(keyword) >= 2 and keyword not in ["예시", "참고", "주의", "중요"]:
                result["keywords"].add(keyword)
    
    # 헤더에서 쟁점 추출
    for pattern in PATTERNS["headers"]:
        for match in re.finditer(pattern, content):
            header = match.group(1).strip()
            # 헤더에서 키워드 추출
            if len(header) >= 2:
                result["keywords"].add(header)
    
    # set을 list로 변환
    return {k: sorted(list(v)) for k, v in result.items()}


def get_source_id(filepath: Path) -> str:
    """파일에서 source_id 추출 (예: part12)"""
    name = filepath.stem.lower()
    
    # part 패턴 찾기
    match = re.search(r"part(\d+)", name)
    if match:
        return f"part{match.group(1).zfill(2)}"
    
    # 파일명 그대로 사용
    return name


def update_index(filepath: Path, index: dict, dry_run: bool = False) -> dict:
    """단일 파일로 인덱스 업데이트"""
    source_id = get_source_id(filepath)
    extracted = extract_from_file(filepath)
    
    # sources 업데이트
    index["sources"][source_id] = extracted
    
    # articles 역인덱스 업데이트
    for article in extracted["articles"]:
        if article not in index.get("articles", {}):
            index["articles"][article] = []
        if source_id not in index["articles"][article]:
            index["articles"][article].append(source_id)
    
    # keywords 역인덱스 업데이트
    for keyword in extracted["keywords"]:
        if keyword not in index.get("keywords", {}):
            index["keywords"][keyword] = []
        if source_id not in index["keywords"][keyword]:
            index["keywords"][keyword].append(source_id)
    
    print(f"[{source_id}] 조문: {len(extracted['articles'])}개, 키워드: {len(extracted['keywords'])}개, 판례: {len(extracted.get('cases', []))}개")
    
    return index


def main():
    parser = argparse.ArgumentParser(description="Auto-Index: 태그 인덱스 자동 업데이트")
    parser.add_argument("file", nargs="?", help="인덱싱할 마크다운 파일")
    parser.add_argument("--dir", "-d", help="인덱싱할 폴더")
    parser.add_argument("--dry-run", action="store_true", help="미리보기 (실제 저장 안함)")
    parser.add_argument("--reset", action="store_true", help="인덱스 초기화 후 재생성")
    
    args = parser.parse_args()
    
    if not args.file and not args.dir:
        parser.print_help()
        sys.exit(1)
    
    # 인덱스 로드
    if args.reset:
        index = {
            "version": "2.0",
            "last_updated": str(date.today()),
            "sources": {},
            "articles": {},
            "keywords": {},
        }
        print("인덱스 초기화됨")
    else:
        index = load_index()
    
    # 파일/폴더 처리
    if args.dir:
        folder = Path(args.dir)
        files = list(folder.glob("*.md"))
        print(f"폴더 '{folder}' 내 {len(files)}개 파일 인덱싱...")
        for f in files:
            index = update_index(f, index, args.dry_run)
    else:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"파일 없음: {filepath}")
            sys.exit(1)
        index = update_index(filepath, index, args.dry_run)
    
    # 저장
    if not args.dry_run:
        save_index(index)
        print(f"\n인덱스 저장됨: {INDEX_PATH}")
    else:
        print("\n[DRY-RUN] 저장하지 않음")
        print(json.dumps(index, ensure_ascii=False, indent=2)[:500] + "...")


if __name__ == "__main__":
    main()
