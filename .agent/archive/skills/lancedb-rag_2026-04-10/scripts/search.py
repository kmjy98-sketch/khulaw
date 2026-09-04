#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LanceDB 고급 벡터 검색 스크립트
- 챕터/편 필터링
- Parent Document Retrieval (챕터 전체 컨텍스트)
- 하이브리드 검색 (키워드 + 벡터)

사용법: 
  python search.py --query "검색어" [옵션]
  
예시:
  python search.py -q "자연인의 권리능력" --top_k 5
  python search.py -q "대리" --chapter "제3장"
  python search.py -q "불법행위" --pdr  # 챕터 전체 반환
  python search.py -q "제750조" --hybrid  # 키워드 + 벡터
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Windows 인코딩
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


ROOT = Path(__file__).resolve().parents[4]
DB_PATH = Path.home() / "AppData" / "Local" / "lancedb" / "law-study-reset-20260319"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def get_model():
    """임베딩 모델 로드 (싱글톤)"""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def get_db():
    """LanceDB 연결"""
    import lancedb
    DB_PATH.mkdir(parents=True, exist_ok=True)
    return lancedb.connect(str(DB_PATH))


def keyword_match_score(text: str, keywords: List[str]) -> float:
    """키워드 매칭 점수 계산 (정규화된 BM25-like)"""
    if not keywords or not text:
        return 0.0
    
    text_lower = text.lower()
    matches = 0
    for kw in keywords:
        if kw.lower() in text_lower:
            matches += 1
    
    return matches / len(keywords)


def extract_keywords(query: str) -> List[str]:
    """쿼리에서 키워드 추출 (조문번호, 법률용어 등)"""
    keywords = []
    
    # 조문 번호 패턴 (제XXX조, 민법 XXX조 등)
    article_pattern = r'제?\d+조(?:의\d+)?'
    articles = re.findall(article_pattern, query)
    keywords.extend(articles)
    
    # 일반 단어 (2자 이상)
    words = re.findall(r'[가-힣a-zA-Z]{2,}', query)
    keywords.extend(words)
    
    return list(set(keywords))


# === Query Expansion 함수 ===

# 법률 키워드 → 상위 개념 매핑 (Step-back용)
LEGAL_CONCEPT_MAP = {
    # 민법총칙
    "제1조": ["민법의 법원", "관습법", "법원"],
    "제2조": ["신의성실", "신의칙", "권리남용"],
    "제3조": ["권리능력", "자연인", "시기"],
    "제4조": ["성년", "미성년자", "행위능력"],
    "자연인": ["권리능력", "행위능력", "주소", "부재자", "실종"],
    "법인": ["권리능력", "설립", "기관", "불법행위능력"],
    "권리능력": ["자연인", "법인", "태아", "사망"],
    "행위능력": ["미성년자", "피성년후견인", "피한정후견인", "제한능력자"],
    
    # 법률행위
    "의사표시": ["법률행위", "효력발생", "하자", "비진의", "통정허위", "착오", "사기", "강박"],
    "무효": ["법률행위", "취소", "불법원인급여"],
    "취소": ["제한능력자", "착오", "사기강박", "추인", "법정추인"],
    "대리": ["법정대리", "임의대리", "무권대리", "표현대리"],
    "무권대리": ["표현대리", "추인", "상대방보호"],
    "조건": ["법률행위", "정지조건", "해제조건"],
    "기한": ["법률행위", "확정기한", "불확정기한"],
    
    # 물권
    "물권변동": ["법률행위", "등기", "인도", "공시", "공신"],
    "등기": ["물권변동", "공시", "추정력", "공신력"],
    "소유권": ["점유권", "용익물권", "담보물권", "취득시효"],
    "점유": ["점유권", "자주점유", "타주점유", "점유보호"],
    "저당권": ["담보물권", "피담보채권", "물상대위", "저당권실행"],
    
    # 채권총론
    "채권": ["급부", "채무불이행", "손해배상", "채권자대위"],
    "채무불이행": ["이행지체", "이행불능", "불완전이행", "손해배상"],
    "손해배상": ["채무불이행", "불법행위", "위자료"],
    "채권자대위권": ["책임재산보전", "피대위권리", "채무자무자력"],
    "채권자취소권": ["책임재산보전", "사해행위", "수익자", "전득자"],
    
    # 채권각론
    "계약": ["청약", "승낙", "계약해제", "위험부담"],
    "매매": ["계약", "하자담보책임", "담보책임"],
    "임대차": ["계약", "임차인보호", "대항력"],
    "불법행위": ["손해배상", "과실", "위법성", "인과관계", "사용자책임"],
    "제750조": ["불법행위", "일반불법행위", "성립요건", "손해배상"],
    "부당이득": ["법률상원인없음", "반환청구", "비채변제"],
}


def expand_query_stepback(query: str) -> List[str]:
    """
    Step-back Prompting: 법률 키워드를 상위 개념으로 확장
    
    예: "제750조" → ["제750조", "불법행위", "일반불법행위", "성립요건", "손해배상"]
    """
    expanded = [query]  # 원본 쿼리 포함
    
    # 조문 번호 추출
    article_match = re.search(r'제?\d+조(?:의\d+)?', query)
    if article_match:
        article = article_match.group()
        if article in LEGAL_CONCEPT_MAP:
            expanded.extend(LEGAL_CONCEPT_MAP[article])
    
    # 법률 용어 추출 및 확장
    keywords = extract_keywords(query)
    for kw in keywords:
        if kw in LEGAL_CONCEPT_MAP:
            expanded.extend(LEGAL_CONCEPT_MAP[kw])
    
    return list(set(expanded))


def generate_hyde_query(query: str) -> str:
    """
    HyDE: 가상 답변 문장 생성 (템플릿 기반, API 호출 X)
    
    쿼리를 법학 교재 스타일 문장으로 변환하여 임베딩 검색 정확도 향상
    """
    # 조문 패턴
    if re.search(r'제?\d+조', query):
        return f"민법 {query}에 관하여, 법률은 다음과 같이 규정하고 있다. 판례는 이에 대해 해석론을 전개하였다."
    
    # 요건/효과 패턴
    if any(kw in query for kw in ["요건", "성립", "효력", "효과"]):
        return f"{query}의 요건과 효과에 관하여 민법은 규정하고 있으며, 판례의 해석론이 있다."
    
    # 비교/차이 패턴
    if any(kw in query for kw in ["차이", "구별", "비교"]):
        return f"{query}에 관한 학설과 판례의 견해 차이를 살펴본다."
    
    # 기본 템플릿
    return f"{query}에 관하여 민법은 규정하고 있으며, 이에 대한 판례와 학설이 있다."


def rerank_results(results: List[Dict], query: str, keywords: List[str]) -> List[Dict]:
    """
    다중 기준 재순위화
    
    점수 = 0.5*벡터 + 0.3*키워드 + 0.2*챕터관련도
    """
    if not results:
        return results
    
    # 챕터 클러스터링 (동일 챕터 결과에 가산점)
    chapter_counts = {}
    for r in results:
        ch = r.get("chapter", "")
        if ch:
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
    
    # 조문번호 정확 매칭 보너스
    article_pattern = r'제?\d+조(?:의\d+)?'
    query_articles = set(re.findall(article_pattern, query))
    
    for r in results:
        vector_score = r.get("_combined_score", 0.5)
        
        # 키워드 매칭 점수
        text = r.get("text", "").lower()
        kw_matches = sum(1 for kw in keywords if kw.lower() in text)
        kw_score = kw_matches / max(len(keywords), 1)
        
        # 조문번호 정확 매칭 보너스
        text_articles = set(re.findall(article_pattern, r.get("text", "")))
        article_bonus = 0.2 if query_articles & text_articles else 0
        
        # 챕터 관련도 (동일 챕터 결과가 많으면 가산점)
        chapter = r.get("chapter", "")
        chapter_score = min(chapter_counts.get(chapter, 0) / 3, 1.0) if chapter else 0
        
        # 종합 점수
        reranked_score = (
            0.5 * vector_score + 
            0.3 * (kw_score + article_bonus) + 
            0.2 * chapter_score
        )
        r["_reranked_score"] = reranked_score
    
    # 재순위 정렬
    results.sort(key=lambda x: x.get("_reranked_score", 0), reverse=True)
    return results


def search(
    query: str, 
    top_k: int = 5, 
    chapter_filter: Optional[str] = None,
    part_filter: Optional[str] = None,
    book_filter: Optional[str] = None,
    pdr: bool = False,
    hybrid: bool = False,
    expand: bool = False,
    rerank: bool = False
) -> List[Dict]:
    """
    고급 벡터 검색 수행
    
    Args:
        query: 검색 쿼리
        top_k: 반환 결과 수
        chapter_filter: 챕터 필터 (예: "제1장", "자연인")
        part_filter: 편 필터 (예: "제1편")
        book_filter: 교재 코드 필터 (예: "1-01")
        pdr: Parent Document Retrieval - True면 챕터 전체 반환
        hybrid: 하이브리드 검색 - 키워드 점수 + 벡터 점수 결합
        expand: Query Expansion - Step-back + HyDE 적용
        rerank: Re-ranking - 다중 기준 재순위화
    
    Returns:
        검색 결과 리스트
    """
    # Query Expansion 적용
    search_queries = [query]
    expanded_terms = []
    if expand:
        expanded_terms = expand_query_stepback(query)
        hyde_query = generate_hyde_query(query)
        search_queries = [query, hyde_query]  # 원본 + HyDE
    
    # 모델 로드 및 쿼리 임베딩
    model = get_model()
    
    # 모든 쿼리로 검색 후 합침
    all_results = []
    seen_chunks = set()
    
    for sq in search_queries:
        query_embedding = model.encode([sq])[0].tolist()
        
        # DB 검색
        db = get_db()
        table = db.open_table("chunks")
        
        # 기본 검색 (더 많이 가져와서 필터링)
        search_limit = top_k * 10 if (chapter_filter or part_filter or book_filter or hybrid or expand) else top_k * 2
        results = table.search(query_embedding).limit(search_limit).to_list()
        
        for r in results:
            chunk_id = r.get("chunk_id", "")
            if chunk_id not in seen_chunks:
                seen_chunks.add(chunk_id)
                all_results.append(r)
    
    results = all_results
    
    # 키워드 추출 (하이브리드/리랝킹용) - 확장 키워드 포함
    keywords = extract_keywords(query)
    if expand and expanded_terms:
        keywords = list(set(keywords + expanded_terms))
    
    # 필터링 및 점수 조정
    filtered = []
    for r in results:
        # 챕터 필터
        if chapter_filter:
            chapter = r.get("chapter", "")
            if chapter_filter not in chapter:
                continue
        
        # 편 필터
        if part_filter:
            part = r.get("part", "")
            if part_filter not in part:
                continue
        
        # 교재 필터
        if book_filter:
            book_code = r.get("book_code", "")
            if book_filter not in book_code:
                continue
        
        # 점수 계산
        vector_score = 1 / (1 + r.get("_distance", 1))  # 거리를 유사도로 변환
        
        if hybrid and keywords:
            text = r.get("text", "")
            kw_score = keyword_match_score(text, keywords)
            # 하이브리드 점수: 70% 벡터 + 30% 키워드
            combined_score = 0.7 * vector_score + 0.3 * kw_score
        else:
            combined_score = vector_score
        
        r["_combined_score"] = combined_score
        filtered.append(r)
    
    # 점수 기준 정렬
    filtered.sort(key=lambda x: x.get("_combined_score", 0), reverse=True)
    
    # Re-ranking 적용
    if rerank:
        filtered = rerank_results(filtered, query, keywords)
    
    # PDR: Parent Document Retrieval - 상위 결과의 챕터 전체 반환
    if pdr and filtered:
        top_chapter = filtered[0].get("chapter", "")
        if top_chapter:
            # 해당 챕터의 모든 페이지 가져오기
            all_data = table.to_arrow()
            chapters = all_data["chapter"].to_pylist()
            
            chapter_pages = []
            for i, ch in enumerate(chapters):
                if ch == top_chapter:
                    row = {col: all_data[col][i].as_py() for col in all_data.column_names if col != "vector"}
                    chapter_pages.append(row)
            
            # 페이지 순서로 정렬
            chapter_pages.sort(key=lambda x: x.get("page", 0))
            filtered = chapter_pages
    
    # 결과 포맷팅
    formatted = []
    for r in filtered[:top_k] if not pdr else filtered:
        formatted.append({
            "book_id": r.get("book_id", ""),
            "book_code": r.get("book_code", ""),
            "citation_title": r.get("citation_title", ""),
            "source_title": r.get("source_title", ""),
            "source_pdf": r.get("source_pdf", ""),
            "page": r.get("page", 0),
            "pdf_page": r.get("pdf_page", 0),
            "chunk_id": r.get("chunk_id", ""),
            "chapter": r.get("chapter", ""),
            "part": r.get("part", ""),
            "chapter_range": r.get("chapter_range", ""),
            "score": round(r.get("_reranked_score", r.get("_combined_score", r.get("_distance", 0))), 4),
            "text_preview": r.get("text", "")[:300] + "..." if len(r.get("text", "")) > 300 else r.get("text", ""),
            "text": r.get("text", ""),  # 전체 텍스트도 포함
            "expanded_terms": expanded_terms if expand else None  # 확장 키워드 정보
        })
    
    return formatted


def list_chapters() -> List[str]:
    """사용 가능한 챕터 목록 반환"""
    db = get_db()
    table = db.open_table("chunks")
    all_data = table.to_arrow()
    
    chapters = set(all_data["chapter"].to_pylist())
    return sorted([ch for ch in chapters if ch], key=lambda x: x)


def main():
    parser = argparse.ArgumentParser(description="LanceDB 고급 벡터 검색")
    parser.add_argument("--query", "-q", required=True, help="검색 쿼리")
    parser.add_argument("--top_k", "-k", type=int, default=5, help="반환 결과 수")
    parser.add_argument("--chapter", "-c", help="챕터 필터 (예: '제1장', '자연인')")
    parser.add_argument("--part", "-p", help="편 필터 (예: '제1편')")
    parser.add_argument("--book", "-b", help="교재 코드 필터 (예: '1-01')")
    parser.add_argument("--pdr", action="store_true", help="Parent Document Retrieval: 챕터 전체 반환")
    parser.add_argument("--hybrid", action="store_true", help="하이브리드 검색 (키워드 + 벡터)")
    parser.add_argument("--expand", "-e", action="store_true", help="Query Expansion (Step-back + HyDE)")
    parser.add_argument("--rerank", "-r", action="store_true", help="Re-ranking (다중 기준 재순위화)")
    parser.add_argument("--json", "-j", action="store_true", help="JSON 출력")
    parser.add_argument("--list-chapters", action="store_true", help="챕터 목록 출력")
    
    args = parser.parse_args()
    
    if args.list_chapters:
        chapters = list_chapters()
        print("\n=== 사용 가능한 챕터 ===")
        for ch in chapters:
            print(f"  - {ch}")
        return
    
    results = search(
        args.query, 
        args.top_k,
        chapter_filter=args.chapter,
        part_filter=args.part,
        book_filter=args.book,
        pdr=args.pdr,
        hybrid=args.hybrid,
        expand=args.expand,
        rerank=args.rerank
    )
    
    if args.json:
        # JSON 출력 시 text 필드 제외 (너무 길어서)
        json_results = [{k: v for k, v in r.items() if k != "text"} for r in results]
        print(json.dumps(json_results, ensure_ascii=False, indent=2))
    else:
        mode = ""
        if args.pdr:
            mode = " [PDR: 챕터 전체]"
        elif args.expand:
            mode = " [Query Expansion]"
        elif args.rerank:
            mode = " [Re-ranking]"
        elif args.hybrid:
            mode = " [하이브리드]"
        if args.expand and args.rerank:
            mode = " [Expand + Rerank]"
        
        print(f"\n=== 검색 결과: '{args.query}'{mode} ===\n")
        
        if args.chapter or args.part:
            filters = []
            if args.chapter:
                filters.append(f"챕터: {args.chapter}")
            if args.part:
                filters.append(f"편: {args.part}")
            print(f"필터: {', '.join(filters)}\n")
        
        for i, r in enumerate(results, 1):
            chapter_info = f" | {r['chapter']}" if r.get('chapter') else ""
            source_label = r.get("citation_title") or r.get("source_title") or r.get("book_id", "")
            if source_label:
                print(f"[{i}] {r['book_code']} | {source_label} p.{r['page']}{chapter_info} (score: {r['score']})")
            else:
                print(f"[{i}] {r['book_code']} p.{r['page']}{chapter_info} (score: {r['score']})")
            print(f"    {r['text_preview']}")
            print()
        
        print(f"총 {len(results)}개 결과")


if __name__ == "__main__":
    main()

