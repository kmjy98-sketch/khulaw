#!/usr/bin/env python3
"""Shared helpers for follow-up legal skills."""

from __future__ import annotations

from pathlib import Path
from string import Formatter
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
STATE_DIR = ROOT / ".agent" / "state"
DEFAULT_PLAYBOOK = STATE_DIR / "legal_playbook.md"
DEFAULT_TEMPLATES = STATE_DIR / "legal_templates.md"
MISSING_NOTE = "자료 부족—보류"
SOURCE_MISSING = "소스에서 확인할 수 없습니다"
NO_HIT = "없음"

from build_socratic_packet import parse_report  # noqa: E402
from load_legal_templates import parse_templates  # noqa: E402
from load_playbook import parse_playbook  # noqa: E402
from render_review import (  # noqa: E402
    counts,
    default_playbook,
    evaluate_clause,
    load_input_text,
    normalize_ws,
    overall_status,
)


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def safe_format(template: str, **values: str) -> str:
    return template.format_map(SafeDict(values))


def load_playbook_data(playbook_path: str | None) -> tuple[dict, str, bool]:
    path = Path(playbook_path) if playbook_path else DEFAULT_PLAYBOOK
    if path.exists():
        return parse_playbook(path), str(path), False
    fallback = default_playbook()
    return fallback, fallback["source"], True


def load_template_data(template_path: str | None) -> tuple[dict, str]:
    path = Path(template_path) if template_path else DEFAULT_TEMPLATES
    data = parse_templates(path)
    return data, str(path)


def select_clauses(
    clauses: list[dict],
    clause_names: list[str] | None = None,
    keyword_tokens: list[str] | None = None,
) -> list[dict]:
    selected: list[dict] = []
    name_set = {name.lower() for name in clause_names or []}
    token_set = {token.lower() for token in keyword_tokens or []}

    for clause in clauses:
        clause_name = clause.get("clause", "").lower()
        keywords = [item.lower() for item in clause.get("keywords", [])]

        if name_set and clause_name in name_set:
            selected.append(clause)
            continue

        if token_set and any(token in clause_name or token in keyword for token in token_set for keyword in keywords):
            selected.append(clause)

    return selected


def analyze_document(
    input_path: str | None,
    inline_text: str | None,
    playbook_path: str | None,
    clause_names: list[str] | None = None,
    keyword_tokens: list[str] | None = None,
) -> dict[str, Any]:
    source_text, source_name = load_input_text(input_path, inline_text)
    normalized_text = normalize_ws(source_text)
    if not normalized_text:
        raise ValueError("입력 문서에서 텍스트를 추출하지 못했습니다.")

    playbook, playbook_source, used_fallback = load_playbook_data(playbook_path)
    clauses = select_clauses(playbook["clauses"], clause_names=clause_names, keyword_tokens=keyword_tokens)
    if not clauses:
        clauses = playbook["clauses"]

    metadata = playbook.get("metadata", {})
    results = [evaluate_clause(normalized_text, clause, metadata) for clause in clauses]
    return {
        "input_name": source_name,
        "playbook_source": playbook_source,
        "used_fallback": used_fallback,
        "results": results,
        "counts": counts(results),
        "overall": overall_status(results),
    }


def load_review_results(review_path: str) -> dict[str, Any]:
    path = Path(review_path)
    if not path.exists():
        raise FileNotFoundError(f"검토 보고서를 찾을 수 없습니다: {path}")

    parsed = parse_report(path.read_text(encoding="utf-8"))
    results = []
    for item in parsed.get("clauses", []):
        normalized = dict(item)
        normalized.setdefault("matched_term", "")
        normalized.setdefault("acceptable_range", "")
        normalized.setdefault("standard_position", "")
        normalized.setdefault("negotiation_priority", "")
        normalized.setdefault("fallback_position", "")
        normalized.setdefault("redline_suggestion", "")
        normalized.setdefault("business_impact", "")
        normalized.setdefault("deviation_note", "")
        normalized.setdefault("trigger_hit", "")
        normalized.setdefault("evidence", MISSING_NOTE)
        results.append(normalized)
    return {
        "input_name": parsed.get("input_name", path.name),
        "playbook_source": "review-report",
        "used_fallback": False,
        "results": results,
        "counts": counts(results),
        "overall": parsed.get("overall_status", overall_status(results)),
    }


def focus_results(results: list[dict]) -> list[dict]:
    focused = [item for item in results if item.get("status") in {"RED", "YELLOW"}]
    return focused or results


def summarize_results(results: list[dict]) -> dict[str, Any]:
    return {
        "results": results,
        "counts": counts(results),
        "overall": overall_status(results),
    }


def portable_issue_rows(results: list[dict]) -> str:
    rows = ["| 조항 | 상태 | 기준 키워드 | 트리거 |", "|---|---|---|---|"]
    for item in results:
        rows.append(
            f"| {item.get('clause', '-')} | {item.get('status', '-')} | "
            f"{item.get('matched_term') or '-'} | {item.get('trigger_hit') or '-'} |"
        )
    return "\n".join(rows)


def portable_clause_sections(results: list[dict]) -> str:
    blocks: list[str] = []
    for item in results:
        lines = [
            f"### {item.get('clause', '-')}",
            f"- 상태: {item.get('status', '-')}",
            f"- matched term: {item.get('matched_term') or NO_HIT}",
            f"- 기준 포지션: {item.get('standard_position') or SOURCE_MISSING}",
            f"- 허용 범위: {item.get('acceptable_range') or SOURCE_MISSING}",
            f"- 협상 우선순위: {item.get('negotiation_priority') or SOURCE_MISSING}",
            f"- fallback 포지션: {item.get('fallback_position') or SOURCE_MISSING}",
            f"- redline 제안: {item.get('redline_suggestion') or SOURCE_MISSING}",
            f"- business impact: {item.get('business_impact') or SOURCE_MISSING}",
            f"- 에스컬레이션 트리거 적중: {item.get('trigger_hit') or NO_HIT}",
            f"- 근거 스니펫: \"{item.get('evidence') or MISSING_NOTE}\"",
        ]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) if blocks else f"- {MISSING_NOTE}"


def render_markdown_template(template_path: Path, variables: dict[str, str]) -> str:
    output = template_path.read_text(encoding="utf-8")
    for key, value in variables.items():
        output = output.replace(f"{{{{{key}}}}}", value)
    return output


def bullet_list(lines: list[str], empty_text: str) -> str:
    if not lines:
        return f"- {empty_text}"
    return "\n".join(f"- {line}" for line in lines)


def compact_snippet(value: str, limit: int = 140) -> str:
    text = normalize_ws(value)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def supported_fields(template: str) -> set[str]:
    return {field_name for _, field_name, _, _ in Formatter().parse(template) if field_name}
