#!/usr/bin/env python3
"""
소크라틱 세션 자동 로더
- 전사문에서 페이지 참조 추출
- 교재 PDF 텍스트 추출 및 캐싱
- LanceDB RAG 검색 통합
- 문제 인덱스 연동

사용법: python socratic_loader.py <transcript_path> [--textbook <pdf_path>] [--rag]
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Windows 인코딩
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 2026-04-10: LanceDB → qmd 전환. .agent/lib/qmd_search.py 사용.
ROOT = Path(__file__).resolve().parents[3]
AGENT_LIB = ROOT / "lib"
if str(AGENT_LIB) not in sys.path:
    sys.path.insert(0, str(AGENT_LIB))


def parse_transcript_pages(transcript_path: str) -> list:
    """
    전사문에서 (페이지 X) 패턴 추출
    반환: [(section_title, page_num), ...]
    """
    content = Path(transcript_path).read_text(encoding="utf-8")
    
    # 패턴: ## N. 제목 (페이지 X)
    pattern = r"## \d+\.\s*(.+?)\s*\(페이지\s*(\d+)\)"
    matches = re.findall(pattern, content)
    
    return [(title, int(page)) for title, page in matches]


def get_page_range(pages: list) -> tuple:
    """페이지 목록에서 최소/최대 범위 추출"""
    if not pages:
        return None, None
    page_nums = [p[1] for p in pages]
    return min(page_nums), max(page_nums)


def extract_textbook_pages(pdf_path: str, start_page: int, end_page: int, cache_dir: str) -> str:
    """
    PDF에서 텍스트 추출 후 캐싱
    캐시 파일이 있으면 캐시 반환
    """
    pdf_name = Path(pdf_path).stem
    cache_file = Path(cache_dir) / f"{pdf_name}_p{start_page}-{end_page}.md"
    
    # 캐시 확인
    if cache_file.exists() and cache_file.stat().st_size > 100:
        print(f"캐시 사용: {cache_file.name}")
        return cache_file.read_text(encoding="utf-8")
    
    # pypdf로 직접 추출
    try:
        from pypdf import PdfReader
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf", "-q"])
        from pypdf import PdfReader
    
    print(f"PDF 추출 중: {Path(pdf_path).name} (p.{start_page}-{end_page})")
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    text_parts = []
    actual_end = min(end_page, total_pages)
    for i in range(start_page - 1, actual_end):
        page_text = reader.pages[i].extract_text()
        if page_text:
            text_parts.append(f"--- Page {i+1} ---\n{page_text}")
    
    text = "\n\n".join(text_parts)
    
    # 캐시 저장
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(text, encoding="utf-8")
    print(f"캐시 저장: {cache_file.name} ({len(text)}자)")
    
    return text


def search_rag(query: str, top_k: int = 5, chapter_filter: str = None, hybrid: bool = True) -> list:
    """
    qmd CLI를 이용한 RAG 검색 (LanceDB 대체, 2026-04-10).

    Args:
        query: 검색 쿼리 (키워드 또는 문장)
        top_k: 반환할 결과 수
        chapter_filter: 특정 폴더/교재명으로 path 필터링 (예: '교재원문', '민법')
        hybrid: 사용하지 않음 (qmd 'query' 모드는 항상 BM25+vec+rerank)

    Returns:
        검색 결과 리스트 [{chunk_id, page, chapter, text_preview, score}, ...]
    """
    try:
        from qmd_search import qmd_search, QmdSearchError
    except ImportError as e:
        print(f"[RAG] qmd_search helper 로드 실패: {e}")
        return []
    try:
        # hybrid=True 면 search(BM25, 빠름), 아니면 vsearch(벡터)
        mode = "search" if hybrid else "vsearch"
        # 필터 위해 더 많이 가져옴
        raw_k = top_k * 4 if chapter_filter else top_k * 2
        hits = qmd_search(query, k=raw_k, mode=mode)
    except QmdSearchError as e:
        print(f"[RAG] qmd 검색 오류: {e}")
        return []

    filtered = []
    for h in hits:
        path = h.get("path", "")
        if chapter_filter and chapter_filter not in path:
            continue
        filtered.append({
            "chunk_id": h.get("docid", ""),
            "page": 0,
            "chapter": path,
            "text_preview": (h.get("snippet") or "")[:200],
            "text": h.get("snippet", ""),
            "title": h.get("title", ""),
            "score": round(float(h.get("score") or 0), 4),
        })
    return filtered[:top_k]


def find_rag_problems(query: str, top_k: int = 5) -> list:
    """
    qmd 검색 결과 중 모의시험·기출문제 파일만 골라 반환 (LanceDB 대체, 2026-04-10).
    """
    try:
        from qmd_search import qmd_search, QmdSearchError
    except ImportError:
        return []
    try:
        hits = qmd_search(query, k=top_k * 6, mode="search")
    except QmdSearchError as e:
        print(f"[RAG_PROBLEM] qmd 검색 오류: {e}")
        return []

    problems = []
    seen_paths = set()
    for h in hits:
        path = h.get("path", "")
        # 모의시험/기출 패턴
        is_exam = (
            re.search(r'(모의시험|변호사시험|기출|문제)', path)
            or re.match(r'.*/[123]\.', path)
        )
        if not is_exam:
            continue
        if path in seen_paths:
            continue
        seen_paths.add(path)

        ptype = "기타"
        if "선택형" in path: ptype = "선택형"
        elif "사례형" in path: ptype = "사례형"
        elif "기록형" in path: ptype = "기록형"

        problems.append({
            "source_type": "rag_exam",
            "subject": "민사법",
            "topic": query,
            "type": ptype,
            "file": path,
            "book_code": Path(path).stem if path else "",
            "score": round(float(h.get("score") or 0), 4),
            "preview": (h.get("snippet") or "")[:100],
        })

    return problems[:top_k]


def find_related_problems(keywords: list, index_path: str) -> list:
    """
    문제 인덱스에서 관련 문제 검색 (v2.0 구조: subjects → topics → problems)
    """
    if not Path(index_path).exists():
        return []
    
    index = json.loads(Path(index_path).read_text(encoding="utf-8"))
    related = []
    
    # v2.0 구조: subjects → topics → problems
    for subject_name, subject_data in index.get("subjects", {}).items():
        for topic_name, topic_data in subject_data.get("topics", {}).items():
            topic_keywords = topic_data.get("keywords", [])
            
            # 키워드 매칭: topic 키워드 또는 topic 이름에 검색어 포함
            if any(kw in topic_keywords for kw in keywords) or \
               any(kw.lower() in topic_name.lower() for kw in keywords):
                
                problems = topic_data.get("problems", {})
                for ptype in ["dt", "case"]:
                    for prob in problems.get(ptype, []):
                        if isinstance(prob, dict):
                            related.append({
                                "subject": subject_name,
                                "topic": topic_name,
                                "type": ptype,
                                **prob
                            })
    
    return related


def prepare_session(transcript_path: str, textbook_path: str = None, 
                   cache_dir: str = None, index_path: str = None,
                   use_rag: bool = False) -> dict:
    """
    소크라틱 세션 준비 - 통합 함수
    
    Args:
        use_rag: True면 LanceDB 벡터 검색으로 관련 교재 청크 자동 로드
    """
    result = {
        "transcript": transcript_path,
        "pages": [],
        "page_range": (None, None),
        "textbook_text": None,
        "related_problems": [],
        "rag_chunks": []  # RAG 검색 결과
    }
    
    # 1. 전사문 페이지 파싱
    pages = parse_transcript_pages(transcript_path)
    result["pages"] = pages
    
    if not pages:
        print("페이지 참조를 찾을 수 없습니다.")
        return result
    
    start, end = get_page_range(pages)
    result["page_range"] = (start, end)
    print(f"페이지 범위: p.{start}-{end}")
    
    # 2. RAG 검색 (전사문 키워드 기반)
    if use_rag:
        keywords = [p[0] for p in pages]  # 섹션 제목
        query = " ".join(keywords[:5])  # 상위 5개 키워드로 검색
        print(f"[RAG] 검색 쿼리: {query[:50]}...")
        
        rag_results = search_rag(query, top_k=5, hybrid=True)
        result["rag_chunks"] = rag_results
        
        if rag_results:
            print(f"[RAG] {len(rag_results)}개 관련 청크 검색됨")
            for r in rag_results[:3]:
                print(f"  - p.{r['page']} {r['chapter']} (score: {r['score']})")
    
    # 3. 교재 텍스트 추출 (캐시)
    if textbook_path and cache_dir:
        result["textbook_text"] = extract_textbook_pages(
            textbook_path, start, end, cache_dir
        )
    
    # 4. 관련 문제 검색 (Index + RAG)
    if index_path:
        keywords = [p[0] for p in pages]
        result["related_problems"] = find_related_problems(keywords, index_path)
    
    # RAG로 기출문제 추가 검색
    if use_rag and result.get("page_range", (None, None))[0]:
        # 키워드가 없으면 전사문 내용 일부 사용하거나 topic 추론 필요하지만, 
        # 여기선 페이지 제목 활용
        rag_query = " ".join([p[0] for p in pages][:3])
        if rag_query:
            rag_problems = find_rag_problems(rag_query, top_k=5)
            if rag_problems:
                print(f"[RAG] 관련 기출문제 {len(rag_problems)}개 발견")
                # 기존 문제 리스트에 병합 (중복 제거 로직 필요시 추가)
                result["related_problems"].extend(rag_problems)
    
    return result


def main():
    parser = argparse.ArgumentParser(description="소크라틱 세션 로더 (RAG 통합)")
    parser.add_argument("transcript", help="전사문 파일 경로")
    parser.add_argument("--textbook", "-t", help="교재 PDF 경로")
    parser.add_argument("--cache", "-c", default="./교재_추출", help="캐시 디렉토리")
    parser.add_argument("--index", "-i", help="문제 인덱스 JSON 경로")
    parser.add_argument("--rag", "-r", action="store_true", help="LanceDB RAG 검색 활성화")
    parser.add_argument("--json", "-j", action="store_true", help="JSON 출력")
    
    args = parser.parse_args()
    
    result = prepare_session(
        args.transcript,
        args.textbook,
        args.cache,
        args.index,
        use_rag=args.rag
    )
    
    if args.json:
        # JSON 출력 (textbook_text, text 제외)
        output = {k: v for k, v in result.items() if k not in ["textbook_text"]}
        output["textbook_extracted"] = bool(result["textbook_text"])
        # rag_chunks에서 text 필드 제거 (너무 길어서)
        if "rag_chunks" in output:
            output["rag_chunks"] = [{k: v for k, v in c.items() if k != "text"} for c in output["rag_chunks"]]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"\n=== 세션 준비 완료 ===")
        print(f"전사문: {result['transcript']}")
        print(f"페이지 범위: p.{result['page_range'][0]}-{result['page_range'][1]}")
        print(f"섹션 수: {len(result['pages'])}")
        print(f"교재 텍스트: {'추출됨' if result['textbook_text'] else '없음'}")
        print(f"RAG 청크: {len(result.get('rag_chunks', []))}개")
        print(f"관련 문제: {len(result['related_problems'])}개")


if __name__ == "__main__":
    main()
