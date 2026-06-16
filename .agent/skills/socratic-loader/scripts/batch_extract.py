#!/usr/bin/env python3
"""
교재 PDF 배치 추출 스크립트
- 모든 교재 PDF → 청크 단위 텍스트 추출
- RAG 2.0 / Reverse-RAG 지원
- 표 구조 탐지 + 페이지 경계 문맥 복원 (pdf-ingest/ingest.py 위임, 2026-04-24)

사용법: python batch_extract.py <pdf_dir> <output_dir> [--chunk-size 30]
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime

# pdf-ingest 공용 추출 함수 재사용 (표 탐지 + 페이지 경계 복원)
_INGEST_PATH = Path(__file__).resolve().parents[2] / "pdf-ingest" / "scripts"
if str(_INGEST_PATH) not in sys.path:
    sys.path.insert(0, str(_INGEST_PATH))

try:
    from pypdf import PdfReader
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf", "-q"])
    from pypdf import PdfReader

try:
    from ingest import extract_pages as _ingest_extract_pages  # type: ignore
except ImportError:
    _ingest_extract_pages = None


def extract_pages(reader, start: int, end: int, pdf_path: str = None) -> str:
    """페이지 범위 텍스트 추출 (표 탐지 + 페이지 경계 복원은 ingest.py 위임)."""
    if _ingest_extract_pages is not None:
        return _ingest_extract_pages(reader, start, end, pdf_path=pdf_path)
    # 폴백: 구버전 동작
    text_parts = []
    for i in range(start - 1, min(end, len(reader.pages))):
        page_text = reader.pages[i].extract_text()
        if page_text:
            text_parts.append(f"--- Page {i+1} ---\n{page_text}")
    return "\n\n".join(text_parts)


def extract_legal_keywords(text: str) -> list:
    """법률 키워드 추출"""
    keywords = set()
    
    # 조문 번호: 제XXX조
    articles = re.findall(r'제\d+조(?:의\d+)?', text)
    keywords.update(articles)
    
    # 판례 번호: XX다XXXX, 대법원 YYYY.M.D
    cases = re.findall(r'\d{2,4}다\d+', text)
    keywords.update(cases)
    
    # 대법원 날짜
    court_dates = re.findall(r'대법원?\s*\d{4}\.\d{1,2}\.\d{1,2}', text)
    keywords.update(court_dates)
    
    return list(keywords)


def batch_extract(pdf_dir: str, output_dir: str, chunk_size: int = 30, 
                  pattern: str = "(1-*)*.pdf") -> dict:
    """
    배치 PDF 추출 (증분 업데이트 지원)
    
    Args:
        pdf_dir: PDF 폴더 경로
        output_dir: 출력 폴더 경로
        chunk_size: 청크당 페이지 수
        pattern: PDF 파일 패턴
    
    Returns:
        추출 결과 인덱스
    """
    pdf_path = Path(pdf_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    index_path = out_path / "chunks_index.json"
    
    # 기존 인덱스 로드 또는 새로 생성
    if index_path.exists():
        try:
            old_index = json.loads(index_path.read_text(encoding="utf-8"))
            if old_index.get("chunk_size") == chunk_size:
                index = old_index
                print(f"기존 인덱스 로드: {len(index['sources'])}개 소스")
            else:
                print("청크 크기 변경됨. 인덱스 초기화.")
                index = {
                    "created": datetime.now().isoformat(),
                    "chunk_size": chunk_size,
                    "sources": [],
                    "chunks": []
                }
        except Exception as e:
            print(f"인덱스 로드 실패 ({e}). 초기화합니다.")
            index = {
                "created": datetime.now().isoformat(),
                "chunk_size": chunk_size,
                "sources": [],
                "chunks": []
            }
    else:
        index = {
            "created": datetime.now().isoformat(),
            "chunk_size": chunk_size,
            "sources": [],
            "chunks": []
        }
    
    # PDF 파일 검색
    pdfs = list(pdf_path.glob(pattern))
    print(f"발견된 PDF: {len(pdfs)}개")
    
    # 처리할 파일명 집합
    processing_files = {p.name for p in pdfs}
    
    # 기존 인덱스에서 현재 처리할 파일들 제거 (업데이트를 위해)
    original_source_count = len(index["sources"])
    index["sources"] = [s for s in index["sources"] if s["file"] not in processing_files]
    index["chunks"] = [c for c in index["chunks"] if c["source"] not in processing_files]
    if len(index["sources"]) < original_source_count:
        print(f"기존 항목 업데이트: {original_source_count - len(index['sources'])}개 파일 재처리")
    
    for pdf in sorted(pdfs):
        print(f"\n처리 중: {pdf.name}")
        
        try:
            reader = PdfReader(str(pdf))
            total_pages = len(reader.pages)
            print(f"  총 페이지: {total_pages}")
            
            source_info = {
                "file": pdf.name,
                "pages": total_pages,
                "chunks": []
            }
            
            # 청크 단위 추출
            for start in range(0, total_pages, chunk_size):
                end = min(start + chunk_size, total_pages)
                
                text = extract_pages(reader, start + 1, end, pdf_path=str(pdf))
                keywords = extract_legal_keywords(text)
                
                # 청크 파일 저장
                chunk_name = f"{pdf.stem}_p{start+1:03d}-{end:03d}.md"
                chunk_path = out_path / chunk_name
                chunk_path.write_text(text, encoding="utf-8")
                
                chunk_info = {
                    "id": f"{pdf.stem}_p{start+1}-{end}",
                    "source": pdf.name,
                    "pages": f"{start+1}-{end}",
                    "file": chunk_name,
                    "size": len(text),
                    "keywords": keywords[:20]  # 상위 20개만
                }
                
                index["chunks"].append(chunk_info)
                source_info["chunks"].append(chunk_name)
                
                print(f"  청크 생성: {chunk_name} ({len(text):,}자, 키워드 {len(keywords)}개)")
            
            index["sources"].append(source_info)
            
        except Exception as e:
            print(f"  오류: {e}")
            continue
    
    # 인덱스 저장
    index["last_updated"] = datetime.now().isoformat()
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n인덱스 저장: {index_path}")
    
    return index


def main():
    parser = argparse.ArgumentParser(description="교재 PDF 배치 추출")
    parser.add_argument("pdf_dir", help="PDF 폴더 경로")
    parser.add_argument("output_dir", help="출력 폴더 경로")
    parser.add_argument("--chunk-size", "-c", type=int, default=30, help="청크당 페이지 수")
    parser.add_argument("--pattern", "-p", default="(1-*)*.pdf", help="PDF 파일 패턴")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("교재 PDF 배치 추출")
    print("=" * 60)
    print(f"PDF 폴더: {args.pdf_dir}")
    print(f"출력 폴더: {args.output_dir}")
    print(f"청크 크기: {args.chunk_size}페이지")
    print("=" * 60)
    
    index = batch_extract(
        args.pdf_dir,
        args.output_dir,
        args.chunk_size,
        args.pattern
    )
    
    print("\n" + "=" * 60)
    print("완료!")
    print(f"총 소스: {len(index['sources'])}개")
    print(f"총 청크: {len(index['chunks'])}개")
    print("=" * 60)


if __name__ == "__main__":
    main()
