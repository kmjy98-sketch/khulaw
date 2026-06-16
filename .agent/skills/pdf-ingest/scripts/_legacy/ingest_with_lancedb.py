#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Ingest - 통합 파이프라인
PDF → 마크다운 추출 → LanceDB 인덱싱

사용법:
  # 전체 파이프라인
  python ingest.py --pdf-dir "민사" --out "pdf_extracts" --index
  
  # 추출만
  python ingest.py --pdf-dir "민사" --out "pdf_extracts" --extract-only
  
  # 인덱싱만
  python ingest.py --md-dir "pdf_extracts" --index-only
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Windows 인코딩
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ============================================================
# 설정
# ============================================================
ROOT = Path(__file__).resolve().parents[4]
DB_PATH = Path.home() / "AppData" / "Local" / "lancedb" / "law-study-reset-20260319"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

AGENT_LIB = ROOT / ".agent" / "lib"
if str(AGENT_LIB) not in sys.path:
    sys.path.append(str(AGENT_LIB))

from source_registry import (
    extract_book_code,
    resolve_source_metadata,
    strip_chunk_suffix,
    strip_code_prefix,
)

# ============================================================
# PDF 추출
# ============================================================

def ensure_pypdf():
    """pypdf 설치 확인"""
    try:
        from pypdf import PdfReader
        return PdfReader
    except ImportError:
        import subprocess
        print("pypdf 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf", "-q"])
        from pypdf import PdfReader
        return PdfReader


def extract_pages(reader, start: int, end: int) -> str:
    """페이지 범위 텍스트 추출"""
    text_parts = []
    for i in range(start - 1, min(end, len(reader.pages))):
        page_text = reader.pages[i].extract_text()
        if page_text:
            text_parts.append(f"--- Page {i+1} ---\n{page_text}")
    return "\n\n".join(text_parts)


def extract_legal_keywords(text: str) -> list:
    """법률 키워드 추출"""
    keywords = set()
    articles = re.findall(r'제\d+조(?:의\d+)?', text)
    keywords.update(articles)
    cases = re.findall(r'\d{2,4}다\d+', text)
    keywords.update(cases)
    return list(keywords)


def batch_extract(pdf_dir: Path, output_dir: Path, chunk_size: int = 30, 
                  pattern: str = "**/*.pdf") -> dict:
    """
    배치 PDF 추출
    """
    PdfReader = ensure_pypdf()
    
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "chunks_index.json"
    
    # 인덱스 로드/생성
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            if index.get("chunk_size") != chunk_size:
                index = {"created": datetime.now().isoformat(), "chunk_size": chunk_size, "sources": [], "chunks": []}
        except:
            index = {"created": datetime.now().isoformat(), "chunk_size": chunk_size, "sources": [], "chunks": []}
    else:
        index = {"created": datetime.now().isoformat(), "chunk_size": chunk_size, "sources": [], "chunks": []}
    
    # PDF 검색
    pdfs = list(pdf_dir.glob(pattern))
    print(f"발견된 PDF: {len(pdfs)}개")
    
    if not pdfs:
        print("PDF 파일 없음")
        return index
    
    # 처리된 파일 추적
    processed = {s["file"] for s in index["sources"]}
    
    for pdf in sorted(pdfs):
        if pdf.name in processed:
            print(f"[건너뜀] {pdf.name} (이미 처리됨)")
            continue
            
        print(f"\n[추출] {pdf.name}")
        
        try:
            reader = PdfReader(str(pdf))
            total_pages = len(reader.pages)
            print(f"  페이지: {total_pages}")

            source_meta = resolve_source_metadata(ROOT, pdf.stem, fallback_title=pdf.stem)
            chunk_base = source_meta["ascii_alias"] or pdf.stem
            source_info = {
                "file": pdf.name,
                "pages": total_pages,
                "chunks": [],
                "source_title": source_meta["source_title"] or pdf.stem,
                "ascii_alias": source_meta["ascii_alias"],
            }
            
            for start in range(0, total_pages, chunk_size):
                end = min(start + chunk_size, total_pages)
                text = extract_pages(reader, start + 1, end)
                
                chunk_name = f"{chunk_base}_p{start+1:03d}-{end:03d}.md"
                (output_dir / chunk_name).write_text(text, encoding="utf-8")
                
                chunk_info = {
                    "id": f"{pdf.stem}_p{start+1}-{end}",
                    "source": pdf.name,
                    "source_title": source_meta["source_title"] or pdf.stem,
                    "ascii_alias": source_meta["ascii_alias"],
                    "pages": f"{start+1}-{end}",
                    "file": chunk_name,
                    "size": len(text),
                    "keywords": extract_legal_keywords(text)[:20]
                }
                
                index["chunks"].append(chunk_info)
                source_info["chunks"].append(chunk_name)
                print(f"  → {chunk_name} ({len(text):,}자)")
            
            index["sources"].append(source_info)
            
        except Exception as e:
            print(f"  [오류] {e}")
    
    index["last_updated"] = datetime.now().isoformat()
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return index

# ============================================================
# LanceDB 인덱싱
# ============================================================

def get_model():
    """임베딩 모델 로드"""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def get_db():
    """LanceDB 연결"""
    import lancedb
    DB_PATH.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(DB_PATH))


def parse_toc_file(toc_path: Path) -> Dict[int, Dict]:
    """목차 파일 파싱"""
    if not toc_path.exists():
        return {}
    
    content = toc_path.read_text(encoding='utf-8')
    chapter_pattern = r'제(\d+)\s*장\s*([^\d\n\r]+?)\s+(\d+)'
    part_pattern = r'제(\d+)\s*편\s+([^\n\r]+?)(?:\s+\d+|\s*$)'
    
    chapters = []
    for match in re.finditer(chapter_pattern, content):
        chapter_num = int(match.group(1))
        chapter_name = match.group(2).strip()
        page_num = int(match.group(3))
        
        # 편 찾기
        part_name = ""
        for pm in re.finditer(part_pattern, content):
            if pm.start() < match.start():
                part_name = f"제{pm.group(1)}편 {pm.group(2).strip()}"
        
        chapters.append({"chapter": f"제{chapter_num}장 {chapter_name}", "part": part_name, "start_page": page_num})
    
    if not chapters:
        return {}
    
    chapters.sort(key=lambda x: x["start_page"])
    
    page_to_chapter = {}
    for i, ch in enumerate(chapters):
        start = ch["start_page"]
        end = chapters[i + 1]["start_page"] - 1 if i + 1 < len(chapters) else 9999
        for p in range(start, end + 1):
            page_to_chapter[p] = {"chapter": ch["chapter"], "part": ch["part"], "chapter_range": f"p{start:03d}-{end:03d}"}
    
    return page_to_chapter


def is_toc_file(file_path: Path) -> bool:
    meta = resolve_source_metadata(
        ROOT,
        file_path.stem,
        fallback_book_code=extract_book_code(file_path.stem),
        fallback_title=strip_code_prefix(strip_chunk_suffix(file_path.stem)),
    )
    title = meta.get("citation_title", "")
    alias = meta.get("ascii_alias", "")
    return "목차" in title or bool(re.search(r"(^|_)toc(_|$)", alias or file_path.stem))


def find_toc_for_file(file_path: Path, toc_files: List[Path]) -> Optional[Path]:
    """청크에 맞는 TOC 자동 매칭"""
    file_title = resolve_source_metadata(
        ROOT,
        file_path.stem,
        fallback_book_code=extract_book_code(file_path.stem),
        fallback_title=strip_code_prefix(strip_chunk_suffix(file_path.stem)),
    )["citation_title"]
    parts = file_title.split('_')
    if len(parts) < 3:
        return None
    
    keywords = [p for p in parts if p and not re.match(r'^\d', p)]
    best_toc, max_score = None, 0
    
    for toc in toc_files:
        if toc.name == file_path.name:
            continue
        toc_title = resolve_source_metadata(
            ROOT,
            toc.stem,
            fallback_book_code=extract_book_code(toc.stem),
            fallback_title=strip_code_prefix(strip_chunk_suffix(toc.stem)),
        )["citation_title"]
        score = sum(1 for kw in keywords if kw in toc_title)
        toc_code = extract_book_code(toc.stem).split('-')[0]
        file_code = extract_book_code(file_path.stem).split('-')[0]
        if file_code and file_code == toc_code:
            score += 2
        if score > max_score and score >= 2:
            max_score, best_toc = score, toc
    
    return best_toc


def detect_page_offset(content: str) -> int:
    """PDF 페이지 → 교재 페이지 오프셋 감지"""
    page_pattern = r'--- Page (\d+) ---'
    page_matches = list(re.finditer(page_pattern, content))
    offset_candidates = []
    
    for pm in page_matches[:10]:
        pdf_page = int(pm.group(1))
        start = pm.end()
        end_match = next((m for m in page_matches if m.start() > pm.start()), None)
        end = end_match.start() if end_match else len(content)
        page_text = content[start:end]
        
        lines = page_text.strip().split('\n')
        last_lines = '\n'.join(lines[-5:]) if len(lines) > 5 else page_text
        footer_match = re.search(r'제\d+장[^\d\n]{0,20}\s+(\d+)\s*$', last_lines, re.MULTILINE)
        if footer_match:
            offset_candidates.append(pdf_page - int(footer_match.group(1)))
    
    if offset_candidates:
        from collections import Counter
        return Counter(offset_candidates).most_common(1)[0][0]
    return 0


def parse_chunk_file(file_path: Path, toc_map: Optional[Dict] = None) -> list:
    """청크 파일 파싱"""
    content = file_path.read_text(encoding='utf-8')
    filename = file_path.stem
    base_stem = strip_chunk_suffix(filename)
    match = re.match(r'(\d+-\d+)_(.+)_p(\d+)-(\d+)', filename)

    if match:
        book_code = match.group(1)
        book_name = match.group(2)
    else:
        book_code_match = re.match(r'(\d+-\d+)_(.+)$', base_stem)
        book_code = book_code_match.group(1) if book_code_match else extract_book_code(base_stem)
        book_name = book_code_match.group(2) if book_code_match else base_stem

    source_meta = resolve_source_metadata(
        ROOT,
        base_stem,
        fallback_book_code=book_code,
        fallback_title=book_name,
    )
    book_code = source_meta["book_code"] or book_code or filename[:4]
    citation_title = source_meta["citation_title"] or book_name
    source_pdf = source_meta["source_pdf"]
    
    page_offset = detect_page_offset(content) if toc_map else 0
    page_pattern = r'--- Page (\d+) ---'
    parts = re.split(page_pattern, content)
    
    pages = []
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            pdf_page = int(parts[i])
            page_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
            textbook_page = pdf_page - page_offset
            
            if page_text and len(page_text) > 50:
                page_data = {
                    "chunk_id": f"{book_code}_p{textbook_page:03d}",
                    "book_id": book_name,
                    "book_code": book_code,
                    "citation_title": citation_title,
                    "source_title": citation_title,
                    "source_pdf": source_pdf,
                    "page": textbook_page,
                    "pdf_page": pdf_page,
                    "text": page_text[:8000],
                    "source_file": file_path.name,
                    "chapter": "",
                    "part": "",
                    "chapter_range": ""
                }
                if toc_map and textbook_page in toc_map:
                    ch = toc_map[textbook_page]
                    page_data.update({"chapter": ch["chapter"], "part": ch["part"], "chapter_range": ch["chapter_range"]})
                pages.append(page_data)
    
    return pages


def index_chunks(md_dir: Path, batch_size: int = 10, reset: bool = False) -> dict:
    """LanceDB 인덱싱"""
    import lancedb
    
    chunk_files = [f for f in md_dir.glob("*.md") if not is_toc_file(f) and f.stem != "range_toc"]
    print(f"청크 파일: {len(chunk_files)}개")
    
    if not chunk_files:
        return {"error": "청크 없음"}
    
    toc_files = [f for f in md_dir.glob("*.md") if is_toc_file(f)]
    toc_cache = {}
    
    print("모델 로드 중...")
    model = get_model()
    db = get_db()
    
    all_pages, chapters_found = [], set()
    
    for i, chunk_file in enumerate(chunk_files):
        try:
            toc = find_toc_for_file(chunk_file, toc_files)
            toc_map = None
            if toc:
                if toc not in toc_cache:
                    toc_cache[toc] = parse_toc_file(toc)
                toc_map = toc_cache[toc]
            
            pages = parse_chunk_file(chunk_file, toc_map)
            all_pages.extend(pages)
            for p in pages:
                if p.get("chapter"):
                    chapters_found.add(p["chapter"])
            
            if i % 20 == 0:
                print(f"  [{i+1}/{len(chunk_files)}] 처리 중...")
        except Exception as e:
            print(f"[오류] {chunk_file.name}: {e}")
    
    print(f"총 페이지: {len(all_pages)}, 챕터: {len(chapters_found)}")
    
    if not all_pages:
        return {"error": "페이지 없음"}
    
    print("임베딩 생성 중...")
    records = []
    for i in range(0, len(all_pages), batch_size):
        batch = all_pages[i:i + batch_size]
        embeddings = model.encode([p["text"] for p in batch], show_progress_bar=False)
        for j, page in enumerate(batch):
            page["vector"] = embeddings[j].tolist()
            records.append(page)
        if i % 100 == 0:
            print(f"  임베딩: {min(i + batch_size, len(all_pages))}/{len(all_pages)}")
    
    print("LanceDB 저장 중...")
    table_name = "chunks"
    if table_name in db.table_names():
        if reset:
            db.drop_table(table_name)
            db.create_table(table_name, records)
        else:
            db.open_table(table_name).add(records)
    else:
        db.create_table(table_name, records)
    
    meta = {"last_updated": datetime.now().isoformat(), "total_chunks": len(records), "chapters": len(chapters_found)}
    (DB_PATH / "index_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    
    return {"success": True, "count": len(records), "chapters": len(chapters_found)}

# ============================================================
# 메인
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="PDF Ingest - 추출 + 인덱싱")
    parser.add_argument("--pdf-dir", help="PDF 소스 디렉토리")
    parser.add_argument("--out", help="마크다운 출력 디렉토리")
    parser.add_argument("--md-dir", help="마크다운 입력 디렉토리 (index-only 시)")
    parser.add_argument("--pattern", default="**/*.pdf", help="PDF 파일 패턴")
    parser.add_argument("--chunk-size", type=int, default=30, help="페이지 분할 단위")
    parser.add_argument("--batch", type=int, default=10, help="임베딩 배치 크기")
    parser.add_argument("--index", action="store_true", help="추출 후 인덱싱")
    parser.add_argument("--extract-only", action="store_true", help="추출만")
    parser.add_argument("--index-only", action="store_true", help="인덱싱만")
    parser.add_argument("--reset", action="store_true", help="인덱스 초기화")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("PDF Ingest Pipeline")
    print("=" * 60)
    
    md_dir = None
    
    # 추출
    if args.pdf_dir and not args.index_only:
        pdf_dir = Path(args.pdf_dir)
        out_dir = Path(args.out) if args.out else Path(".agent/data/pdf_extracts")
        print(f"\n[1/2] PDF 추출: {pdf_dir} → {out_dir}")
        batch_extract(pdf_dir, out_dir, args.chunk_size, args.pattern)
        md_dir = out_dir
    
    # 인덱싱
    if (args.index or args.index_only) and not args.extract_only:
        if args.md_dir:
            md_dir = Path(args.md_dir)
        elif not md_dir:
            md_dir = Path(args.out) if args.out else Path(".agent/data/pdf_extracts")
        
        print(f"\n[2/2] LanceDB 인덱싱: {md_dir}")
        result = index_chunks(md_dir, args.batch, args.reset)
        print(f"결과: {result}")
    
    print("\n" + "=" * 60)
    print("완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
