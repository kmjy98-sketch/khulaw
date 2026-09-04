#!/usr/bin/env python3
"""
PDF 텍스트 추출기
사용법: python pdf_reader.py <pdf_path> [--output <output_path>] [--pages <start>-<end>]
"""

import argparse
import sys
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    print("pypdf가 설치되어 있지 않습니다. 설치 중...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf", "-q"])
    from pypdf import PdfReader


def extract_text(pdf_path: str, start_page: int = None, end_page: int = None) -> str:
    """PDF에서 텍스트 추출"""
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    start = (start_page - 1) if start_page else 0
    end = end_page if end_page else total_pages
    
    text_parts = []
    for i in range(start, min(end, total_pages)):
        page_text = reader.pages[i].extract_text()
        if page_text:
            text_parts.append(f"--- Page {i+1} ---\n{page_text}")
    
    return "\n\n".join(text_parts)


def main():
    parser = argparse.ArgumentParser(description="PDF 텍스트 추출기")
    parser.add_argument("pdf_path", help="PDF 파일 경로")
    parser.add_argument("--output", "-o", help="출력 파일 경로 (.md 또는 .txt)")
    parser.add_argument("--pages", "-p", help="페이지 범위 (예: 1-10)")
    parser.add_argument("--quiet", "-q", action="store_true", help="콘솔 출력 생략")
    
    args = parser.parse_args()
    
    # 페이지 범위 파싱
    start_page, end_page = None, None
    if args.pages:
        parts = args.pages.split("-")
        start_page = int(parts[0])
        end_page = int(parts[1]) if len(parts) > 1 else start_page
    
    # 텍스트 추출
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"파일을 찾을 수 없습니다: {pdf_path}")
        sys.exit(1)
    
    print(f"PDF 읽는 중: {pdf_path.name}")
    text = extract_text(str(pdf_path), start_page, end_page)
    
    # 출력
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(text, encoding="utf-8")
        print(f"저장됨: {output_path}")
    
    if not args.quiet:
        print("\n" + "="*60 + "\n")
        print(text[:5000])  # 처음 5000자만 출력
        if len(text) > 5000:
            print(f"\n... (총 {len(text)}자, 전체 내용은 --output으로 저장)")
    
    return text


if __name__ == "__main__":
    main()
