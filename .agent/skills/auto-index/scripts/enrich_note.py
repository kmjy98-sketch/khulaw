#!/usr/bin/env python3
"""
Enrich Note: 마크다운 노트에 위키 스타일 링크([[키워드]]), 태그, 관련 노트를 자동 주입
"""

import argparse
import json
import re
import sys
from pathlib import Path
from collections import Counter

# 설정
SCRIPT_DIR = Path(__file__).parent
INDEX_PATH = SCRIPT_DIR.parent.parent.parent / "state" / "tag_index.json"
CONCEPT_DIR = Path(r"h:\내 드라이브\민사\민법\개념")


def load_index(index_path: Path = INDEX_PATH) -> dict:
    """인덱스 파일 로드"""
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"Warning: Index file not found at {index_path}")
    return {"keywords": {}, "articles": {}, "sources": {}, "note_keywords": {}}


def get_all_keywords(index_data: dict) -> dict:
    """
    tag_index.json의 note_keywords 섹션에서 키워드→파일 매핑 생성
    Returns: {키워드: 파일명} 딕셔너리
    """
    keyword_map = {}
    
    # note_keywords 섹션만 사용 (정확한 키워드-파일 매핑)
    for note_file, keywords in index_data.get("note_keywords", {}).items():
        for kw in keywords:
            # 최소 4자 이상 키워드만 (노이즈 방지)
            if len(kw) >= 4 and kw not in keyword_map:
                keyword_map[kw] = note_file
    
    return keyword_map


def extract_keywords_from_file(content: str) -> list:
    """
    노트 본문에서 키워드 추출 (조문번호, 개념 등)
    Returns: 추출된 키워드 리스트
    """
    keywords = []
    
    # 조문번호 패턴 (제XXX조)
    article_pattern = r"제(\d+)조"
    for match in re.finditer(article_pattern, content):
        keywords.append(f"제{match.group(1)}조")
    
    # 판례번호 패턴
    case_pattern = r"(\d{4}다\d+)"
    for match in re.finditer(case_pattern, content):
        keywords.append(match.group(1))
    
    # 헤더에서 키워드 추출
    header_pattern = r"^#+\s*(.+)$"
    for match in re.finditer(header_pattern, content, re.MULTILINE):
        header = match.group(1).strip()
        if len(header) >= 2 and len(header) <= 30:
            keywords.append(header)
    
    return list(set(keywords))


def inject_inline_links(content: str, keyword_map: dict, current_file: str = None) -> str:
    """
    본문 키워드를 [[키워드]] 형식으로 변환
    - 이미 링크된 영역([[...]])은 건너뜀
    - 자기 자신 파일로의 링크는 제외
    - 코드 블록, YAML frontmatter 제외
    """
    # 1. 기존 링크 영역 보호 - [[...]] 패턴을 플레이스홀더로 대체
    link_pattern = r'\[\[[^\]]+\]\]'
    placeholders = []
    
    def save_link(match):
        placeholders.append(match.group(0))
        return f"__LINK_PLACEHOLDER_{len(placeholders)-1}__"
    
    protected_content = re.sub(link_pattern, save_link, content)
    
    # 2. 코드 블록 보호
    code_blocks = []
    code_pattern = r'```[\s\S]*?```|`[^`]+`'
    
    def save_code(match):
        code_blocks.append(match.group(0))
        return f"__CODE_PLACEHOLDER_{len(code_blocks)-1}__"
    
    protected_content = re.sub(code_pattern, save_code, protected_content)
    
    # 3. YAML frontmatter 보호 (파일 시작의 ---...---)
    frontmatter_match = re.match(r'^---\s*\n[\s\S]*?\n---\s*\n', protected_content)
    frontmatter = ""
    if frontmatter_match:
        frontmatter = frontmatter_match.group(0)
        protected_content = protected_content[len(frontmatter):]
    
    # 4. 긴 키워드부터 처리 (부분 매칭 방지)
    sorted_keywords = sorted(keyword_map.keys(), key=len, reverse=True)
    
    for keyword in sorted_keywords:
        target_file = keyword_map[keyword]
        
        # 자기 자신은 링크하지 않음
        if current_file and target_file == current_file:
            continue
        
        # 너무 짧은 키워드는 제외 (노이즈 방지)
        if len(keyword) < 2:
            continue
        
        escaped_kw = re.escape(keyword)
        
        # 단어 경계 고려 (한글은 \b가 안 먹으므로 간단히 처리)
        pattern = rf'{escaped_kw}'
        
        # 첫 번째 매칭만 교체 (과도한 링크 방지)
        new_content = re.sub(pattern, f"[[{keyword}]]", protected_content, count=1)
        
        if new_content != protected_content:
            protected_content = new_content
    
    # 5. frontmatter 복원
    protected_content = frontmatter + protected_content
    
    # 6. 코드 블록 복원
    for i, code in enumerate(code_blocks):
        protected_content = protected_content.replace(f"__CODE_PLACEHOLDER_{i}__", code)
    
    # 7. 기존 링크 복원
    for i, link in enumerate(placeholders):
        protected_content = protected_content.replace(f"__LINK_PLACEHOLDER_{i}__", link)
    
    return protected_content



def update_tags(content: str, keywords: list) -> str:
    """
    frontmatter 또는 footer에 태그 추가
    Bear 앱 호환: #태그 형식
    """
    # 이미 태그 섹션이 있는지 확인
    if "## Tags" in content or "#민법" in content:
        return content  # 이미 태그가 있으면 스킵
    
    # 주요 키워드만 태그로 (최대 5개)
    main_tags = []
    for kw in keywords[:5]:
        # 공백을 언더스코어로, 특수문자 제거
        tag = re.sub(r"[^\w가-힣]", "", kw)
        if tag:
            main_tags.append(f"#{tag}")
    
    if main_tags:
        tag_section = f"\n\n---\n\n{' '.join(main_tags)}\n"
        content = content.rstrip() + tag_section
    
    return content


def append_related_notes(content: str, current_id: str, index_data: dict, keywords: list) -> str:
    """
    관련 노트 섹션 추가
    같은 키워드를 공유하는 노트들을 '관련 노트'로 추가
    """
    # 이미 관련 노트 섹션이 있으면 스킵
    if "## 관련 노트" in content or "## Related" in content:
        return content
    
    related = []
    note_keywords = index_data.get("note_keywords", {})
    
    # 현재 파일의 키워드와 겹치는 다른 노트 찾기
    current_keywords_set = set(keywords)
    
    for note_file, note_kws in note_keywords.items():
        if note_file == current_id:
            continue
        
        overlap = current_keywords_set & set(note_kws)
        if overlap:
            related.append((note_file, len(overlap)))
    
    # 관련도 높은 순으로 정렬, 최대 5개
    related.sort(key=lambda x: x[1], reverse=True)
    related = related[:5]
    
    if related:
        related_section = "\n\n## 관련 노트\n\n"
        for note_file, _ in related:
            note_name = note_file.replace(".md", "").replace("_", " ")
            related_section += f"- [[{note_name}]]\n"
        content = content.rstrip() + related_section
    
    return content


def main():
    parser = argparse.ArgumentParser(description="Enrich Note: 위키 링크 및 태그 자동 주입")
    parser.add_argument("file", help="대상 마크다운 파일")
    parser.add_argument("--index", help="사용할 인덱스 파일 경로 (선택)", default=None)
    parser.add_argument("--dry-run", action="store_true", help="변경사항 미리보기 (저장 안함)")
    
    args = parser.parse_args()
    filepath = Path(args.file)
    
    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)
        
    content = filepath.read_text(encoding="utf-8")
    original_content = content
    
    # 1. 인덱스 로드
    index_path = Path(args.index) if args.index else INDEX_PATH
    index_data = load_index(index_path)
    all_keywords = get_all_keywords(index_data)
    
    print(f"Loaded {len(all_keywords)} keywords from index")
    
    # 2. 현재 파일의 키워드 추출 (태그용)
    current_keywords = extract_keywords_from_file(content)
    
    # 3. 인라인 링크 주입
    content = inject_inline_links(content, all_keywords, filepath.name)
    
    # 4. 태그 추가 (선택적)
    # content = update_tags(content, current_keywords)
    
    # 5. 관련 노트 추가 (선택적)
    # current_id = filepath.name
    # content = append_related_notes(content, current_id, index_data, current_keywords)
    
    # 변경사항 출력/저장
    if content != original_content:
        if args.dry_run:
            print(f"[DRY RUN] Would update {filepath.name}")
            # 변경된 부분 표시
            import difflib
            diff = difflib.unified_diff(
                original_content.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"a/{filepath.name}",
                tofile=f"b/{filepath.name}"
            )
            print("".join(diff))
        else:
            filepath.write_text(content, encoding="utf-8")
            print(f"Updated {filepath.name}: Injected links")
    else:
        print(f"No changes made to {filepath.name}")


if __name__ == "__main__":
    main()
