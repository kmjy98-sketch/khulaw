#!/usr/bin/env python3
"""
Batch Link: 개념 노트 일괄 링크 업데이트
- 백업 생성
- 각 노트에 enrich_note.py 적용
- 결과 보고
"""

import os
import shutil
import json
import re
from pathlib import Path
from datetime import datetime

# 설정
SCRIPT_DIR = Path(__file__).parent
CONCEPT_DIR = Path(r"E:\법학볼트\1.민사\92.개념")
ARCHIVE_DIR = CONCEPT_DIR / "_archive"
INDEX_PATH = SCRIPT_DIR.parent.parent.parent / "state" / "tag_index.json"


def load_index() -> dict:
    """인덱스 파일 로드"""
    if INDEX_PATH.exists():
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"note_keywords": {}}


def get_keyword_map(index_data: dict) -> dict:
    """키워드→파일 매핑 생성"""
    keyword_map = {}
    for note_file, keywords in index_data.get("note_keywords", {}).items():
        for kw in keywords:
            if len(kw) >= 4 and kw not in keyword_map:
                keyword_map[kw] = note_file
    return keyword_map


def backup_files():
    """개념 노트 백업"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = ARCHIVE_DIR / f"backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for md_file in CONCEPT_DIR.glob("*.md"):
        shutil.copy2(md_file, backup_dir / md_file.name)
        count += 1
    
    print(f"Backed up {count} files to {backup_dir}")
    return backup_dir


def inject_links(content: str, keyword_map: dict, current_file: str) -> str:
    """키워드에 [[]] 링크 주입"""
    # 1. 기존 링크 보호
    link_pattern = r'\[\[[^\]]+\]\]'
    placeholders = []
    
    def save_link(match):
        placeholders.append(match.group(0))
        return f"__LINK_{len(placeholders)-1}__"
    
    protected = re.sub(link_pattern, save_link, content)
    
    # 2. 코드 블록 보호
    code_blocks = []
    code_pattern = r'```[\s\S]*?```|`[^`]+`'
    
    def save_code(match):
        code_blocks.append(match.group(0))
        return f"__CODE_{len(code_blocks)-1}__"
    
    protected = re.sub(code_pattern, save_code, protected)
    
    # 3. YAML frontmatter 보호
    fm_match = re.match(r'^---\s*\n[\s\S]*?\n---\s*\n', protected)
    frontmatter = ""
    if fm_match:
        frontmatter = fm_match.group(0)
        protected = protected[len(frontmatter):]
    
    # 4. 키워드 링크 주입 (긴 것부터)
    sorted_keywords = sorted(keyword_map.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        target_file = keyword_map[keyword]
        
        # 자기 자신은 링크하지 않음
        if target_file == current_file:
            continue
        
        escaped_kw = re.escape(keyword)
        # 첫 번째 매칭만 교체
        protected = re.sub(escaped_kw, f"[[{keyword}]]", protected, count=1)
    
    # 5. 복원
    protected = frontmatter + protected
    
    for i, code in enumerate(code_blocks):
        protected = protected.replace(f"__CODE_{i}__", code)
    
    for i, link in enumerate(placeholders):
        protected = protected.replace(f"__LINK_{i}__", link)
    
    return protected


def process_all_notes(keyword_map: dict, dry_run: bool = False):
    """모든 노트 처리"""
    updated = 0
    skipped = 0
    errors = []
    
    # 처리 대상 파일
    md_files = [f for f in CONCEPT_DIR.glob("*.md") 
                if not f.name.startswith(("Source_", "README", "link_notes", "split_notes"))]
    
    print(f"Processing {len(md_files)} files...")
    
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            new_content = inject_links(content, keyword_map, md_file.name)
            
            if new_content != content:
                if not dry_run:
                    md_file.write_text(new_content, encoding="utf-8")
                print(f"  Updated: {md_file.name}")
                updated += 1
            else:
                skipped += 1
        except Exception as e:
            errors.append((md_file.name, str(e)))
    
    print(f"\n=== Results ===")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")
    if errors:
        print(f"Errors: {len(errors)}")
        for name, err in errors:
            print(f"  - {name}: {err}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="개념 노트 일괄 링크 업데이트")
    parser.add_argument("--dry-run", action="store_true", help="변경사항 미리보기")
    parser.add_argument("--no-backup", action="store_true", help="백업 건너뛰기")
    
    args = parser.parse_args()
    
    # 1. 인덱스 로드
    index_data = load_index()
    keyword_map = get_keyword_map(index_data)
    print(f"Loaded {len(keyword_map)} keywords")
    
    # 2. 백업
    if not args.no_backup and not args.dry_run:
        backup_files()
    
    # 3. 처리
    process_all_notes(keyword_map, args.dry_run)


if __name__ == "__main__":
    main()
