#!/usr/bin/env python3
"""Convert a legal review report into a Socratic packet JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUTPUT = ROOT / ".agent" / "state" / "legal_socratic_packet.json"
MISSING_NOTE = "자료 부족—보류"
NO_HIT = "없음"


def capture(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else default


def parse_report(text: str) -> dict:
    input_name = capture(r"^- 입력 문서: (.+)$", text, "unknown")
    overall_status = capture(r"^- Overall: (GREEN|YELLOW|RED)$", text, "YELLOW")

    clause_block_match = re.search(
        r"## (조항별 검토|조항별 근거)\n(?P<body>.*?)(?:\n## |\Z)",
        text,
        flags=re.DOTALL,
    )
    clause_block = clause_block_match.group("body").strip() if clause_block_match else ""
    sections = re.split(r"(?m)^### ", clause_block)
    clause_entries = []
    for section in sections:
        lines = section.strip().splitlines()
        if not lines:
            continue
        clause_name = lines[0].strip()
        body = "\n".join(lines[1:])

        clause_entries.append(
            {
                "clause": clause_name,
                "status": capture(r"- 상태: (GREEN|YELLOW|RED)", body, "YELLOW"),
                "matched_term": capture(r"- matched term: (.+)", body, ""),
                "standard_position": capture(r"- 기준 포지션: (.+)", body),
                "acceptable_range": capture(r"- 허용 범위: (.+)", body),
                "negotiation_priority": capture(r"- 협상 우선순위: (.+)", body),
                "fallback_position": capture(r"- fallback 포지션: (.+)", body),
                "redline_suggestion": capture(r"- redline 제안: (.+)", body),
                "business_impact": capture(r"- business impact: (.+)", body),
                "deviation_note": capture(r"- 편차 판단: (.+)", body),
                "trigger_hit": capture(r"- 에스컬레이션 트리거 적중: (.+)", body, NO_HIT),
                "evidence": capture(r'- 근거 스니펫: "(.+)"', body, MISSING_NOTE),
            }
        )

    return {
        "input_name": input_name,
        "overall_status": overall_status,
        "clauses": clause_entries,
    }


def build_question(clause: dict) -> dict:
    clause_name = clause["clause"]
    status = clause["status"]
    if status == "RED":
        question = f"{clause_name} 조항이 왜 RED인지 문서 근거와 business impact를 연결해 설명해보세요."
        hint = "트리거 적중, redline 제안, fallback 포지션을 함께 보세요."
    elif status == "YELLOW":
        question = f"{clause_name} 조항에서 누락되었거나 불명확한 요소가 무엇인지 설명해보세요."
        hint = "플레이북 기준 포지션과 현재 문구 사이의 빈칸을 찾으세요."
    else:
        question = f"{clause_name} 조항이 왜 GREEN인지 근거 스니펫과 기준 포지션으로 설명해보세요."
        hint = "문서 문구가 플레이북 기준과 어떻게 맞는지 말해보세요."

    return {
        "clause": clause_name,
        "status": status,
        "question": question,
        "hint": hint,
        "evidence": clause.get("evidence", MISSING_NOTE),
        "redline_suggestion": clause.get("redline_suggestion", ""),
        "business_impact": clause.get("business_impact", ""),
    }


def retrieval_queries(clauses: list[dict]) -> list[str]:
    queries: list[str] = []
    for clause in clauses:
        if clause["status"] == "GREEN":
            continue
        queries.append(clause["clause"])
        trigger_hit = clause.get("trigger_hit")
        if trigger_hit and trigger_hit != NO_HIT:
            queries.append(f"{clause['clause']} {trigger_hit}")
        redline = clause.get("redline_suggestion")
        if redline:
            queries.append(f"{clause['clause']} {redline}")
    return queries


def main() -> None:
    parser = argparse.ArgumentParser(description="검토 보고서를 소크라틱 패킷으로 변환")
    parser.add_argument("review_path", help="render_review.py가 생성한 마크다운 보고서 경로")
    parser.add_argument("--output", "-o", default=str(DEFAULT_OUTPUT), help="출력 JSON 경로")
    args = parser.parse_args()

    review_path = Path(args.review_path)
    if not review_path.exists():
        raise FileNotFoundError(f"검토 보고서를 찾을 수 없습니다: {review_path}")

    report_text = review_path.read_text(encoding="utf-8")
    parsed = parse_report(report_text)

    focus_clauses = [clause for clause in parsed["clauses"] if clause["status"] in {"RED", "YELLOW"}]
    if not focus_clauses:
        focus_clauses = parsed["clauses"]

    packet = {
        "mode": "legal-socratic",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_review": str(review_path),
        "input_name": parsed["input_name"],
        "overall_status": parsed["overall_status"],
        "focus_clauses": focus_clauses,
        "questions": [build_question(clause) for clause in focus_clauses],
        "retrieval_queries": retrieval_queries(focus_clauses),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"소크라틱 패킷 저장됨: {output_path}")


if __name__ == "__main__":
    main()
