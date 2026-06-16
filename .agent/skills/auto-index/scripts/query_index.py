#!/usr/bin/env python3
"""
Auto-Index Query: 태그 인덱스 조회
"""

import argparse
import json
import sys
from pathlib import Path

INDEX_PATH = Path(__file__).parent.parent.parent.parent / "state" / "tag_index.json"


def load_index() -> dict:
    """인덱스 로드"""
    if not INDEX_PATH.exists():
        print(f"인덱스 파일 없음: {INDEX_PATH}")
        sys.exit(1)
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def query_article(index: dict, article: str) -> None:
    """조문 검색"""
    # 정규화
    if not article.endswith("조"):
        article = f"{article}조"
    article = article.replace("제", "")
    
    sources = index.get("articles", {}).get(article, [])
    if sources:
        print(f"[{article}] 포함된 파트: {', '.join(sources)}")
    else:
        print(f"[{article}] 검색 결과 없음")


def query_keyword(index: dict, keyword: str) -> None:
    """키워드 검색"""
    sources = index.get("keywords", {}).get(keyword, [])
    if sources:
        print(f"[{keyword}] 포함된 파트: {', '.join(sources)}")
    else:
        print(f"[{keyword}] 검색 결과 없음")


def query_source(index: dict, source_id: str) -> None:
    """특정 파트 내용 조회"""
    source = index.get("sources", {}).get(source_id, {})
    if source:
        print(f"[{source_id}]")
        print(f"  조문: {', '.join(source.get('articles', []))}")
        print(f"  키워드: {', '.join(source.get('keywords', []))}")
        if source.get("cases"):
            print(f"  판례: {', '.join(source.get('cases', []))}")
    else:
        print(f"[{source_id}] 검색 결과 없음")


def list_all(index: dict) -> None:
    """전체 통계"""
    sources = index.get("sources", {})
    articles = index.get("articles", {})
    keywords = index.get("keywords", {})
    
    print(f"[태그 인덱스 통계]")
    print(f"  마지막 업데이트: {index.get('last_updated', 'N/A')}")
    print(f"  파트 수: {len(sources)}")
    print(f"  조문 수: {len(articles)}")
    print(f"  키워드 수: {len(keywords)}")


def main():
    parser = argparse.ArgumentParser(description="Auto-Index Query: 태그 인덱스 조회")
    parser.add_argument("--article", "-a", help="조문 검색 (예: 126조)")
    parser.add_argument("--keyword", "-k", help="키워드 검색 (예: 표현대리)")
    parser.add_argument("--source", "-s", help="특정 파트 조회 (예: part12)")
    parser.add_argument("--list", "-l", action="store_true", help="전체 통계")
    
    args = parser.parse_args()
    
    if not any([args.article, args.keyword, args.source, args.list]):
        parser.print_help()
        sys.exit(1)
    
    index = load_index()
    
    if args.article:
        query_article(index, args.article)
    elif args.keyword:
        query_keyword(index, args.keyword)
    elif args.source:
        query_source(index, args.source)
    elif args.list:
        list_all(index)


if __name__ == "__main__":
    main()
