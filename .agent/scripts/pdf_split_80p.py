#!/usr/bin/env python3
"""
PDF 80페이지 단위 분할 도구 (v3.5 운영용)

용도:
  한국 로스쿨 단권화 PDF(500~1500p)를 Gemini 3.1 Pro 안전 처리 단위로 분할.
  - Gemini 3.1 Pro PDF 한계: 50MB / 1,000페이지 / 출력 64K 토큰
  - 한국 법학 PDF는 한자·각주 밀도로 페이지당 토큰 무거움
  - 기본 분할 단위: 80페이지 (안정적 토큰 여유 확보)

사용법:
  python pdf_split_80p.py <input.pdf> [--pages 80] [--out-dir ./chunks]
  
  예시:
    python pdf_split_80p.py 형법총론.pdf
    python pdf_split_80p.py 헌법쟁점정리.pdf --pages 100 --out-dir ./split
    python pdf_split_80p.py "경로/물권법.pdf"

출력 파일명:
  {원본명}_p001-080.pdf, {원본명}_p081-160.pdf, ...
  
의존성:
  pip install pypdf
  (또는: pip install pypdf2 — 자동 fallback)

설계 원칙:
  - 페이지 경계 정확 보존 (압축·재인코딩 안 함)
  - 메타데이터(제목·저자) 청크 파일에 상속
  - 처리 로그 (split_log.txt) 자동 생성 → coverage_rule 검증용
  - 큰 파일(>50MB chunk) 발생 시 경고
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime
from pathlib import Path

# Windows cp949 인코딩 문제 방지
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# pypdf (권장) → PyPDF2 fallback
try:
    from pypdf import PdfReader, PdfWriter

    PDF_LIB = "pypdf"
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter

        PDF_LIB = "PyPDF2"
    except ImportError:
        sys.stderr.write(
            "ERROR: pypdf 또는 PyPDF2 필요\n"
            "  설치: pip install pypdf\n"
        )
        sys.exit(1)


GEMINI_PDF_LIMIT_MB = 50
GEMINI_PDF_LIMIT_PAGES = 1000


def split_pdf(
    input_path: Path,
    pages_per_chunk: int = 80,
    out_dir: Path | None = None,
) -> dict:
    """
    PDF를 N페이지 단위로 분할.
    
    Returns:
        분할 결과 dict (로그 파일에도 동일 내용 기록)
    """
    if not input_path.exists():
        raise FileNotFoundError(f"입력 PDF 없음: {input_path}")
    if input_path.suffix.lower() != ".pdf":
        raise ValueError(f"PDF 파일이 아님: {input_path}")

    out_dir = out_dir or input_path.parent / f"{input_path.stem}_chunks"
    out_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(input_path))
    total_pages = len(reader.pages)
    
    if total_pages == 0:
        raise ValueError("페이지 0개 PDF")
    
    # 메타데이터 백업
    metadata = dict(reader.metadata) if reader.metadata else {}

    chunks_info = []
    
    print(f"[입력] {input_path.name} - 총 {total_pages}페이지")
    print(f"[분할 단위] {pages_per_chunk}페이지")
    print(f"[출력 디렉토리] {out_dir}")
    print(f"[PDF 라이브러리] {PDF_LIB}")
    print("-" * 60)
    
    chunk_idx = 0
    for start in range(0, total_pages, pages_per_chunk):
        end = min(start + pages_per_chunk, total_pages)
        chunk_idx += 1
        
        writer = PdfWriter()
        
        # 페이지 추가
        for page_num in range(start, end):
            writer.add_page(reader.pages[page_num])
        
        # 메타데이터 상속
        if metadata:
            try:
                writer.add_metadata(metadata)
            except Exception:
                pass  # 메타데이터 오류는 무시 (내용 보존이 우선)
        
        # 파일명: 원본명_pNNN-MMM.pdf (1-based 페이지 번호로 사용자 친화)
        chunk_name = f"{input_path.stem}_p{start + 1:04d}-{end:04d}.pdf"
        chunk_path = out_dir / chunk_name
        
        with open(chunk_path, "wb") as f:
            writer.write(f)
        
        chunk_size_mb = chunk_path.stat().st_size / (1024 * 1024)
        
        # 안전 경고
        warnings = []
        if chunk_size_mb > GEMINI_PDF_LIMIT_MB:
            warnings.append(
                f"!! {chunk_size_mb:.1f}MB - Gemini API 50MB 한계 초과. "
                f"--pages 값을 더 낮추세요."
            )
        if (end - start) > GEMINI_PDF_LIMIT_PAGES:
            warnings.append(
                f"!! {end - start}p - Gemini 1,000p 한계 초과."
            )
        
        chunk_info = {
            "chunk_index": chunk_idx,
            "filename": chunk_name,
            "page_range": f"{start + 1}-{end}",
            "page_count": end - start,
            "size_mb": round(chunk_size_mb, 2),
            "warnings": warnings,
        }
        chunks_info.append(chunk_info)
        
        # 진행 출력
        warn_str = f" {'; '.join(warnings)}" if warnings else ""
        print(
            f"청크 {chunk_idx:02d} | {chunk_name} | "
            f"p{start + 1:04d}-{end:04d} ({end - start}p, "
            f"{chunk_size_mb:.1f}MB){warn_str}"
        )
    
    # split_log.txt 생성 (coverage_rule 검증용)
    log_path = out_dir / "split_log.txt"
    log_data = {
        "source": input_path.name,
        "source_total_pages": total_pages,
        "pages_per_chunk": pages_per_chunk,
        "chunks": chunks_info,
        "generated_at": datetime.now().isoformat(),
        "pdf_library": PDF_LIB,
        "v3.5_anchor_template": (
            "각 청크를 Gemini AI Studio에 업로드할 때 사용자 메시지에 "
            "다음 한 줄을 첨부:\n"
            "  CHUNK: pages {page_range} | total {page_count} pages | "
            "source: {source} | mode: full extraction"
        ),
    }
    log_path.write_text(
        json.dumps(log_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    
    print("-" * 60)
    print(f"[완료] 총 {chunk_idx}개 청크 생성")
    print(f"[로그] {log_path}")
    print()
    print("다음 단계:")
    print("  1. 각 청크를 AI Studio에 1개씩 업로드")
    print("  2. 사용자 메시지에 anchor 한 줄 첨부 (split_log.txt 참고)")
    print("  3. 01번 system instruction이 [FIDELITY_CONTRACT]를 강제함")
    
    return log_data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PDF 80페이지 단위 자동 분할 (v3.5 운영용)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input_pdf",
        type=Path,
        help="입력 PDF 파일 경로",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=80,
        help="청크당 페이지 수 (기본 80)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="출력 디렉토리 (기본: <input>_chunks/)",
    )
    
    args = parser.parse_args()
    
    if args.pages < 10 or args.pages > 500:
        sys.stderr.write(
            f"ERROR: --pages는 10~500 사이여야 합니다 (입력: {args.pages})\n"
            "  권장: 80 (Gemini 3.1 Pro 안전 단위)\n"
        )
        return 1
    
    try:
        split_pdf(args.input_pdf, args.pages, args.out_dir)
        return 0
    except FileNotFoundError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 2
    except Exception as e:
        sys.stderr.write(f"ERROR: 분할 실패 - {type(e).__name__}: {e}\n")
        return 3


if __name__ == "__main__":
    sys.exit(main())
