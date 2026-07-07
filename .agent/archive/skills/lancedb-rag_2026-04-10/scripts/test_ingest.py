#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LanceDB 청크 인덱싱 스크립트
- 교재 청크 파일을 페이지 단위로 분할
- 목차 파일 기반 챕터 메타데이터 자동 추가
- 임베딩 생성 및 LanceDB 저장

사용법: 
  python ingest.py --dir <청크폴더> [--toc <목차파일>] [--batch 10]
  
예시:
python ingest.py --dir "1.민사/30.송영곤_기본민법/교재_추출" --toc "1.민사/30.송영곤_기본민법/교재_추출/1-00_목차.md"
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Windows 인코딩
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


DB_PATH = Path("h:/내 드라이브/test_ingest/lancedb")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def get_model():
    """임베딩 모델 로드 (캐싱)"""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def get_db():
    """LanceDB 연결"""
    import lancedb
    DB_PATH.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(DB_PATH))


def parse_toc_file(toc_path: Path) -> Dict[int, Dict]:
    """
    목차 파일을 파싱하여 페이지별 챕터 정보 매핑 생성
    
    반환: {페이지번호: {"chapter": "제1장 자연인", "part": "제1편 권리의 주체와 대리", "chapter_range": "p013-042"}}
    """
    if not toc_path.exists():
        print(f"[경고] 목차 파일 없음: {toc_path}")
        return {}
    
    content = toc_path.read_text(encoding='utf-8')
    
    # 챕터 정보 추출 패턴들
    # 제N편 제목
    part_pattern = r'제(\d+)\s*편\s+([^\n\r]+?)(?:\s+\d+|\s*$)'
    # 제N장 제목 페이지번호 (예: "제1장자연인 13", "제2장 법인 • 비법인단체 43")
    chapter_pattern = r'제(\d+)\s*장\s*([^\d\n\r]+?)\s+(\d+)'
    # 제N절 형태도 있음
    section_pattern = r'제(\d+)\s*절\s+([^\d\n\r]+?)\s+(\d+)'
    
    chapters = []
    current_part = ""
    
    # 편 정보 먼저 추출
    parts = {}
    for match in re.finditer(part_pattern, content):
        part_num = int(match.group(1))
        part_name = f"제{part_num}편 {match.group(2).strip()}"
        # 편 다음에 나오는 첫 번째 챕터의 페이지를 찾아야 함
        parts[part_num] = part_name
    
    # 장 정보 추출
    for match in re.finditer(chapter_pattern, content):
        chapter_num = int(match.group(1))
        chapter_name = match.group(2).strip()
        page_num = int(match.group(3))
        
        # 해당 장이 속한 편 찾기 (패턴 위치 기반)
        match_pos = match.start()
        current_part_name = ""
        for part_match in re.finditer(part_pattern, content):
            if part_match.start() < match_pos:
                part_num = int(part_match.group(1))
                current_part_name = f"제{part_num}편 {part_match.group(2).strip()}"
        
        chapters.append({
            "chapter": f"제{chapter_num}장 {chapter_name}",
            "part": current_part_name,
            "start_page": page_num
        })
    
    if not chapters:
        print("[경고] 목차에서 챕터 정보를 찾을 수 없음")
        return {}
    
    # 챕터별 페이지 범위 계산 (다음 챕터 시작 - 1)
    chapters.sort(key=lambda x: x["start_page"])
    
    page_to_chapter = {}
    for i, ch in enumerate(chapters):
        start_page = ch["start_page"]
        # 다음 챕터 시작 전까지
        if i + 1 < len(chapters):
            end_page = chapters[i + 1]["start_page"] - 1
        else:
            end_page = 9999  # 마지막 챕터
        
        chapter_range = f"p{start_page:03d}-{end_page:03d}"
        
        for page in range(start_page, end_page + 1):
            page_to_chapter[page] = {
                "chapter": ch["chapter"],
                "part": ch["part"],
                "chapter_range": chapter_range
            }
    
    print(f"[목차] {len(chapters)}개 챕터 파싱 완료")
    for ch in chapters[:5]:  # 처음 5개만 출력
        print(f"  - {ch['chapter']} (p{ch['start_page']}~)")
    if len(chapters) > 5:
        print(f"  ... 외 {len(chapters) - 5}개")
    
    return page_to_chapter


def detect_page_offset(content: str) -> int:
    """
    청크 내용에서 교재 페이지 번호를 감지하여 오프셋 계산
    
    교재 하단에는 "제N장 제목 XX" 형식으로 페이지 번호가 있음
    예: "제1장자연인 15" → 교재 페이지 15
    
    반환: offset (PDF 페이지 - offset = 교재 페이지)
    """
    # 페이지 하단 패턴: "제N장제목 페이지번호" 또는 "숫자 제N장"
    footer_patterns = [
        r'제\d+장[^\d\n]{1,20}\s+(\d+)\s*$',  # "제1장자연인 15"
        r'^(\d+)\s+제\d+장',                    # "15 제1장자연인"
        r'--- Page (\d+) ---.*?(?:제\d+장[^\d\n]{1,20})\s+(\d+)',  # Page N과 페이지번호 동시 감지
    ]
    
    # 여러 페이지에서 오프셋 후보 수집
    offset_candidates = []
    
    # 정규식으로 Page N과 교재 페이지 번호 쌍 찾기
    page_pattern = r'--- Page (\d+) ---'
    page_matches = list(re.finditer(page_pattern, content))
    
    for pm in page_matches:
        pdf_page = int(pm.group(1))
        # 해당 페이지 영역 추출 (다음 Page 마커 전까지)
        start = pm.end()
        next_match = None
        for next_pm in page_matches:
            if next_pm.start() > pm.start():
                next_match = next_pm
                break
        end = next_match.start() if next_match else len(content)
        page_text = content[start:end]
        
        # 페이지 하단에서 교재 페이지 번호 찾기 (마지막 몇 줄)
        lines = page_text.strip().split('\n')
        last_lines = '\n'.join(lines[-5:]) if len(lines) > 5 else page_text
        
        # "제N장제목 XX" 패턴
        footer_match = re.search(r'제\d+장[^\d\n]{0,20}\s+(\d+)\s*$', last_lines, re.MULTILINE)
        if footer_match:
            textbook_page = int(footer_match.group(1))
            offset = pdf_page - textbook_page
            offset_candidates.append(offset)
    
    # 가장 빈번한 오프셋 선택 (투표 방식)
    if offset_candidates:
        from collections import Counter
        most_common = Counter(offset_candidates).most_common(1)
        if most_common:
            return most_common[0][0]
    
    return 0  # 기본 오프셋 (감지 실패 시)


def parse_chunk_file(file_path: Path, toc_map: Optional[Dict[int, Dict]] = None) -> list:
    """
    청크 파일을 페이지 단위로 분할
    --- Page N --- 마커 기준
    toc_map이 있으면 챕터 정보도 추가 (오프셋 자동 감지)
    """
    content = file_path.read_text(encoding='utf-8')
    
    # 파일명에서 메타데이터 추출
    # 예: 1-01_민법_송영곤_기본민강_권리주체(26)_p001-030.md
    filename = file_path.stem
    match = re.match(r'(\d+-\d+)_(.+)_p(\d+)-(\d+)', filename)
    
    if match:
        book_code = match.group(1)
        book_name = match.group(2)
        file_page_start = int(match.group(3))
        file_page_end = int(match.group(4))
    else:
        book_code = filename[:4]
        book_name = filename
        file_page_start = 1
        file_page_end = 9999
    
    # 오프셋 자동 감지 (PDF 페이지 → 교재 페이지 변환)
    page_offset = detect_page_offset(content) if toc_map else 0
    
    # --- Page N --- 기준 분할
    page_pattern = r'--- Page (\d+) ---'
    parts = re.split(page_pattern, content)
    
    pages = []
    if len(parts) > 1:
        # 페이지 마커가 있는 경우
        for i in range(1, len(parts), 2):
            pdf_page_num = int(parts[i])
            page_text = parts[i + 1].strip() if i + 1 < len(parts) else ""
            
            # 교재 페이지 번호 계산 (오프셋 적용)
            textbook_page = pdf_page_num - page_offset
            
            if page_text and len(page_text) > 50:  # 최소 50자
                page_data = {
                    "chunk_id": f"{book_code}_p{textbook_page:03d}",
                    "book_id": book_name,
                    "book_code": book_code,
                    "page": textbook_page,  # 교재 페이지 번호 사용
                    "pdf_page": pdf_page_num,  # PDF 물리 페이지도 저장
                    "text": page_text[:8000],  # 최대 8000자
                    "source_file": file_path.name,
                    # 챕터 정보 기본값
                    "chapter": "",
                    "part": "",
                    "chapter_range": ""
                }
                
                # 목차 정보로 챕터 메타데이터 추가 (교재 페이지 기준)
                if toc_map and textbook_page in toc_map:
                    ch_info = toc_map[textbook_page]
                    page_data["chapter"] = ch_info.get("chapter", "")
                    page_data["part"] = ch_info.get("part", "")
                    page_data["chapter_range"] = ch_info.get("chapter_range", "")
                
                pages.append(page_data)
    else:
        # 페이지 마커가 없는 경우 전체를 하나로
        if len(content) > 50:
            page_data = {
                "chunk_id": f"{book_code}_full",
                "book_id": book_name,
                "book_code": book_code,
                "page": file_page_start,
                "pdf_page": file_page_start,
                "text": content[:8000],
                "source_file": file_path.name,
                "chapter": "",
                "part": "",
                "chapter_range": ""
            }
            
            if toc_map and file_page_start in toc_map:
                ch_info = toc_map[file_page_start]
                page_data["chapter"] = ch_info.get("chapter", "")
                page_data["part"] = ch_info.get("part", "")
                page_data["chapter_range"] = ch_info.get("chapter_range", "")
            
            pages.append(page_data)
    
    # 오프셋 정보 출력 (디버깅용)
    if page_offset != 0 and pages:
        print(f"    [오프셋 감지] PDF→교재: -{page_offset} (예: PDF p{pages[0].get('pdf_page', '?')} → 교재 p{pages[0].get('page', '?')})")
    
    return pages


def ingest_chunks(chunk_dir: Path, toc_path: Optional[Path] = None, batch_size: int = 10, reset: bool = False) -> dict:
    """
    청크 파일들을 LanceDB에 인덱싱
    reset=True이면 기존 테이블 삭제 후 새로 생성
    """
    import lancedb
    import pyarrow as pa
    
    # 목차 파싱 (있으면)
    toc_map = {}
    if toc_path:
        toc_map = parse_toc_file(toc_path)
    
    # 청크 파일 목록 (목차 파일 제외)
    chunk_files = [f for f in chunk_dir.glob("*.md") 
                   if not f.stem.endswith("목차") and "목차" not in f.stem]
    print(f"발견된 청크 파일: {len(chunk_files)}개")
    
    if not chunk_files:
        return {"error": "청크 파일 없음", "count": 0}
    
    # 모델 로드
    print("임베딩 모델 로드 중...")
    model = get_model()
    print(f"모델 로드 완료: {MODEL_NAME}")
    
    # DB 연결
    db = get_db()
    
    # 모든 페이지 파싱
    all_pages = []
    chapters_found = set()
    for i, chunk_file in enumerate(chunk_files):
        try:
            pages = parse_chunk_file(chunk_file, toc_map)
            all_pages.extend(pages)
            
            # 챕터 통계
            for p in pages:
                if p.get("chapter"):
                    chapters_found.add(p["chapter"])
            
            print(f"[{i+1}/{len(chunk_files)}] {chunk_file.name}: {len(pages)}페이지")
        except Exception as e:
            print(f"[오류] {chunk_file.name}: {e}")
    
    print(f"\n총 페이지 수: {len(all_pages)}")
    if chapters_found:
        print(f"챕터 매핑: {len(chapters_found)}개 챕터")
    
    if not all_pages:
        return {"error": "파싱된 페이지 없음", "count": 0}
    
    # 배치 임베딩
    print(f"\n임베딩 생성 중 (배치 크기: {batch_size})...")
    
    records = []
    for i in range(0, len(all_pages), batch_size):
        batch = all_pages[i:i + batch_size]
        texts = [p["text"] for p in batch]
        
        # 임베딩 생성
        embeddings = model.encode(texts, show_progress_bar=False)
        
        for j, page in enumerate(batch):
            page["vector"] = embeddings[j].tolist()
            records.append(page)
        
        print(f"  임베딩: {min(i + batch_size, len(all_pages))}/{len(all_pages)}")
    
    # LanceDB 저장
    print("\nLanceDB 저장 중...")
    
    # 테이블 생성 또는 업데이트
    table_name = "chunks"
    
    if table_name in db.table_names():
        if reset:
            # 기존 테이블 삭제 후 새로 생성
            db.drop_table(table_name)
            print("[초기화] 기존 테이블 삭제")
            table = db.create_table(table_name, records)
            print(f"새 테이블 생성: {len(records)}개")
        else:
            # 기존 테이블에 추가 (스키마 호환 필요)
            table = db.open_table(table_name)
            table.add(records)
            print(f"기존 테이블에 추가: {len(records)}개")
    else:
        # 새 테이블 생성
        table = db.create_table(table_name, records)
        print(f"새 테이블 생성: {len(records)}개")
    
    # 인덱스 메타데이터 저장
    meta = {
        "last_updated": datetime.now().isoformat(),
        "total_chunks": len(records),
        "source_files": len(chunk_files),
        "model": MODEL_NAME,
        "toc_used": str(toc_path) if toc_path else None,
        "chapters_mapped": len(chapters_found)
    }
    meta_path = DB_PATH / "index_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    
    return {
        "success": True,
        "count": len(records),
        "files": len(chunk_files),
        "chapters": len(chapters_found),
        "db_path": str(DB_PATH)
    }


def main():
    parser = argparse.ArgumentParser(description="LanceDB 청크 인덱싱 (챕터 메타데이터 지원)")
    parser.add_argument("--dir", "-d", required=True, help="청크 파일 디렉토리")
    parser.add_argument("--toc", "-t", help="목차 파일 경로 (선택, 챕터 메타데이터 추가)")
    parser.add_argument("--batch", "-b", type=int, default=10, help="배치 크기")
    parser.add_argument("--reset", "-r", action="store_true", help="기존 테이블 삭제 후 새로 생성")
    
    args = parser.parse_args()
    
    chunk_dir = Path(args.dir)
    if not chunk_dir.exists():
        print(f"오류: 디렉토리 없음 - {chunk_dir}")
        sys.exit(1)
    
    toc_path = Path(args.toc) if args.toc else None
    if toc_path and not toc_path.exists():
        print(f"[경고] 목차 파일 없음: {toc_path}")
        toc_path = None
    
    result = ingest_chunks(chunk_dir, toc_path, args.batch, args.reset)
    
    print("\n" + "=" * 50)
    print("인덱싱 완료!")
    print(f"  총 청크: {result.get('count', 0)}개")
    print(f"  소스 파일: {result.get('files', 0)}개")
    print(f"  챕터 매핑: {result.get('chapters', 0)}개")
    print(f"  DB 경로: {result.get('db_path', 'N/A')}")


if __name__ == "__main__":
    main()
