#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Ingest - 추출 전용 (2026-04-10 LanceDB → qmd 전환 후)

PDF → 마크다운 청크 추출. 인덱싱은 sync/_교재원문/ 배치 후 qmd가 자동 처리.
LanceDB 인덱싱 코드는 scripts/_legacy/ingest_with_lancedb.py에 보존.

사용법:
  python ingest.py --pdf-dir "민사" --out "pdf_extracts"
  python ingest.py --pdf-dir "민사" --out "pdf_extracts" --pattern "*.pdf" --chunk-size 30
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


_SENT_END = re.compile(r'[.!?）\]】」』다함음됨임없있]\s*$')
_CONN_START = re.compile(r'^[의를이가은는에서도과와로으부터까지만도]')


def _table_to_markdown(table: list) -> str:
    """pdfplumber 표(list of list) → 마크다운 표."""
    if not table or not table[0]:
        return ""
    # None 셀 → 빈 문자열, 줄바꿈 → 공백
    def clean(cell):
        if cell is None:
            return ""
        return str(cell).replace("\n", " ").strip()

    rows = [[clean(c) for c in row] for row in table if any(c for c in row)]
    if not rows:
        return ""
    n_cols = max(len(r) for r in rows)
    for r in rows:
        r += [""] * (n_cols - len(r))

    sep = ["---"] * n_cols
    lines = ["| " + " | ".join(rows[0]) + " |",
             "| " + " | ".join(sep) + " |"]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _repair_page_boundaries(text: str) -> str:
    """
    --- Page N --- 마커 앞뒤 문맥 끊김 복원.
    이전 줄이 종결기호 없이 끝나고 다음 줄이 조사/어미로 시작하면 공백으로 연결.
    """
    PAGE_RE = re.compile(r'\n\n--- Page (\d+) ---\n')
    parts = PAGE_RE.split(text)
    if len(parts) <= 1:
        return text

    out = [parts[0]]
    idx = 1
    while idx < len(parts):
        page_num = parts[idx]
        page_text = parts[idx + 1] if idx + 1 < len(parts) else ""
        idx += 2
        prev_last = out[-1].rstrip().split("\n")[-1] if out[-1].strip() else ""
        next_first = page_text.lstrip().split("\n")[0] if page_text.strip() else ""
        if (prev_last and next_first
                and not _SENT_END.search(prev_last)
                and _CONN_START.match(next_first)
                and not next_first.startswith(("#", "-", ">", "|"))):
            out[-1] = out[-1].rstrip() + page_text
        else:
            out.append(f"\n\n--- Page {page_num} ---\n")
            out.append(page_text)
    return "".join(out)


def _extract_page_pdfplumber(pdf_path: str, page_idx: int) -> str:
    """pdfplumber로 단일 페이지 추출. 표 구조 우선, 없으면 일반 텍스트."""
    try:
        import pdfplumber
    except ImportError:
        return None  # fallback to pypdf

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_idx >= len(pdf.pages):
                return ""
            page = pdf.pages[page_idx]
            tables = page.find_tables()
            if not tables:
                return page.extract_text() or ""

            # 표와 일반 텍스트를 Y 순서로 인터리브
            # 표 영역의 bounding box 수집
            table_bboxes = [t.bbox for t in tables]
            table_mds = {i: _table_to_markdown(t.extract()) for i, t in enumerate(tables)}

            # 표 영역을 제외한 일반 텍스트 (crop 활용)
            page_height = page.height
            result_blocks = []  # (y_top, text_or_table_md)

            # 표 바운딩박스를 Y 정렬
            sorted_tables = sorted(enumerate(table_bboxes), key=lambda x: x[1][1])

            prev_y = 0
            for tidx, (t_x0, t_y0, t_x1, t_y1) in sorted_tables:
                # 표 위의 일반 텍스트
                if t_y0 > prev_y:
                    above = page.crop((0, prev_y, page.width, t_y0)).extract_text()
                    if above and above.strip():
                        result_blocks.append((prev_y, above.strip()))
                # 표 자체
                result_blocks.append((t_y0, table_mds[tidx]))
                prev_y = t_y1

            # 마지막 표 아래 텍스트
            if prev_y < page_height:
                below = page.crop((0, prev_y, page.width, page_height)).extract_text()
                if below and below.strip():
                    result_blocks.append((prev_y, below.strip()))

            return "\n\n".join(block for _, block in result_blocks)
    except Exception:
        return None  # fallback to pypdf


def extract_pages(reader, start: int, end: int, pdf_path: str = None) -> str:
    """페이지 범위 텍스트 추출. pdfplumber 우선(표 탐지), fallback pypdf."""
    text_parts = []
    for i in range(start - 1, min(end, len(reader.pages))):
        page_text = None
        if pdf_path:
            page_text = _extract_page_pdfplumber(pdf_path, i)
        if page_text is None:
            page_text = reader.pages[i].extract_text() or ""
        if page_text.strip():
            text_parts.append(f"--- Page {i+1} ---\n{page_text}")
    raw = "\n\n".join(text_parts)
    return _repair_page_boundaries(raw)


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
                text = extract_pages(reader, start + 1, end, pdf_path=str(pdf))
                
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
# 메인
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="PDF Ingest - 추출 (qmd 전환 후 인덱싱은 자동)")
    parser.add_argument("--pdf-dir", required=True, help="PDF 소스 디렉토리")
    parser.add_argument("--out", help="마크다운 출력 디렉토리")
    parser.add_argument("--pattern", default="**/*.pdf", help="PDF 파일 패턴")
    parser.add_argument("--chunk-size", type=int, default=30, help="페이지 분할 단위")
    # 호환용 폐기 플래그 (경고만 출력)
    parser.add_argument("--index", action="store_true", help="(폐기됨) qmd가 자동 인덱싱")
    parser.add_argument("--index-only", action="store_true", help="(폐기됨) qmd가 자동 인덱싱")
    parser.add_argument("--extract-only", action="store_true", help="(이제 기본 동작)")
    parser.add_argument("--md-dir", help="(폐기됨)")
    parser.add_argument("--batch", type=int, default=10, help="(폐기됨)")
    parser.add_argument("--reset", action="store_true", help="(폐기됨)")

    args = parser.parse_args()

    if args.index or args.index_only or args.md_dir or args.reset:
        print("[경고] LanceDB 인덱싱 옵션은 폐기됨. 추출만 수행.")
        print("       인덱싱은 sync/_교재원문/ 배치 후 `qmd update && qmd embed` 로 처리.")
        print("       레거시 코드: .agent/skills/pdf-ingest/scripts/_legacy/ingest_with_lancedb.py")

    print("=" * 60)
    print("PDF Ingest - 추출 전용")
    print("=" * 60)

    pdf_dir = Path(args.pdf_dir)
    out_dir = Path(args.out) if args.out else Path(".agent/data/pdf_extracts")
    print(f"\n[추출] {pdf_dir} → {out_dir}")
    batch_extract(pdf_dir, out_dir, args.chunk_size, args.pattern)

    print("\n" + "=" * 60)
    print("완료! 후속 단계:")
    print(f"  1) 청크를 sync/_교재원문/ 하위로 배치 (.agent/tmp/textbook_migrate.py 참조)")
    print(f"  2) qmd update && qmd embed")
    print("=" * 60)


if __name__ == "__main__":
    main()
