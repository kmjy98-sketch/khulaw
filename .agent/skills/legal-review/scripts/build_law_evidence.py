#!/usr/bin/env python3
"""
legal_review.md에서 법령·판례 참조를 추출하고 korean-law-mcp tools.py를 직접 호출해
법리 근거 JSON을 생성한다. run_legal_suite.py 6번째 스텝에서 호출된다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[3]
# #49 korean-law-mcp 은퇴 → law_api.py(법제처 직접 API) 재배선. law_api가 자체 API 키(_load_key)를 로드한다.
LIB_DIR = ROOT / ".agent" / "lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

# 한국 법령명 패턴 (e.g. 민법, 형법, 근로기준법)
_LAW_CITE_RE = re.compile(r"([가-힣]{2,}법(?:률)?)\s*제\s*(\d+)\s*조", re.UNICODE)
_LAW_NAME_RE = re.compile(r"([가-힣]{2,}법(?:률)?)", re.UNICODE)
# 판례 인용 패턴:
#   "대법원 2024다12345", "대법원 2024. 1. 1. 선고 2023다12345 판결" 등
_PREC_RE = re.compile(
    r"(대법원|헌법재판소|고등법원|지방법원)\s+"
    r"(?:\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.\s*선고\s+)?"
    r"(\d{4})[가-힣]\d+",
    re.UNICODE,
)
_NOISE_NAMES = {"법원", "법인", "법무", "법리", "법령", "법관", "법학", "법안", "법제"}


def extract_references(text: str) -> dict:
    """review 텍스트에서 법령명·조문 번호·판례 참조를 추출한다."""
    law_citations: list[dict] = []
    for m in _LAW_CITE_RE.finditer(text):
        law_citations.append(
            {"law_name": m.group(1), "article": m.group(2), "full": m.group(0)}
        )

    law_names: set[str] = set()
    for m in _LAW_NAME_RE.finditer(text):
        name = m.group(1)
        if len(name) >= 2 and name not in _NOISE_NAMES:
            law_names.add(name)
    for c in law_citations:
        law_names.add(c["law_name"])

    precedent_refs: list[dict] = []
    for m in _PREC_RE.finditer(text):
        precedent_refs.append(
            {"court": m.group(1), "year": m.group(2), "full": m.group(0)}
        )

    return {
        "law_names": sorted(law_names),
        "law_citations": law_citations,
        "precedent_refs": precedent_refs,
    }


def _import_tools():
    """law_api(법제처 직접 API) 임포트. 실패 시 None 반환. (#49 korean-law-mcp 대체)"""
    try:
        from law_api import search_law, get_law_detail, search_precedent  # type: ignore
        return search_law, get_law_detail, search_precedent
    except Exception:
        return None, None, None


def query_laws(law_names: list[str]) -> list[dict]:
    """법령명 목록으로 korean-law-mcp를 조회한다. 최대 5건."""
    search_law, get_law_detail, _ = _import_tools()
    if search_law is None:
        return [{"error": "korean-law-mcp import 실패 — 의존성 설치 확인 필요"}]

    results: list[dict] = []
    for name in law_names[:5]:
        sr = search_law(query=name, page=1, page_size=3)
        if "error" in sr:
            results.append({"law_name": name, "search_error": sr["error"]})
            continue
        laws = sr.get("laws", [])
        if not laws:
            results.append({"law_name": name, "found": False})
            continue
        top = laws[0]
        law_id = top.get("법령ID", "")
        detail: dict = {}
        if law_id and get_law_detail:
            detail = get_law_detail(law_id=law_id)
        results.append(
            {
                "law_name": name,
                "found": True,
                "top_match": top,
                "articles_count": len(detail.get("조문", [])),
                "sample_articles": detail.get("조문", [])[:5],
            }
        )
    return results


def query_precedents(precedent_refs: list[dict]) -> list[dict]:
    """판례 참조 목록으로 korean-law-mcp를 조회한다. 최대 3건."""
    if not precedent_refs:
        return []
    _, _, search_precedent = _import_tools()
    if search_precedent is None:
        return [{"error": "korean-law-mcp import 실패"}]

    results: list[dict] = []
    seen: set[str] = set()
    for ref in precedent_refs[:3]:
        query = ref.get("full", "")
        if query in seen:
            continue
        seen.add(query)
        court = ref.get("court")
        sr = search_precedent(query=query, page=1, page_size=3, court=court)
        results.append({"query": query, "court": court, "result": sr})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="법리 근거 조회 — korean-law-mcp 직접 연동"
    )
    parser.add_argument("review_path", help="legal_review.md 경로")
    parser.add_argument("--output", "-o", required=True, help="출력 JSON 경로")
    args = parser.parse_args()

    review_path = Path(args.review_path)
    if not review_path.exists():
        print(f"[skip] 검토 보고서 없음: {review_path}", file=sys.stderr)
        raise SystemExit(0)

    api_key = os.environ.get("LAW_API_KEY", "")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("[skip] LAW_API_KEY 미설정 — korean-law-mcp 스텝 건너뜀", file=sys.stderr)
        # 빈 결과 파일 생성 (아티팩트 경로 통일)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "skipped": True,
                    "reason": "LAW_API_KEY 미설정",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        raise SystemExit(0)

    review_text = review_path.read_text(encoding="utf-8")
    refs = extract_references(review_text)

    law_evidence = query_laws(refs["law_names"])
    precedent_evidence = query_precedents(refs["precedent_refs"])

    output_data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_review": str(review_path),
        "extracted_references": refs,
        "law_evidence": law_evidence,
        "precedent_evidence": precedent_evidence,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"법리 근거 저장됨: {output_path}")
    print(
        f"조회 법령: {len(law_evidence)}건 / "
        f"판례: {len(precedent_evidence)}건 / "
        f"참조 조문: {sum(r.get('articles_count', 0) for r in law_evidence if 'articles_count' in r)}건"
    )


if __name__ == "__main__":
    main()
