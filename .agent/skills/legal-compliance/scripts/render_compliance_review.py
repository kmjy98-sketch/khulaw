#!/usr/bin/env python3
"""Render a compliance-oriented legal review report."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[4]
LEGAL_REVIEW_SCRIPTS = ROOT / ".agent" / "skills" / "legal-review" / "scripts"

if str(LEGAL_REVIEW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(LEGAL_REVIEW_SCRIPTS))

from legal_suite_utils import (  # noqa: E402
    DEFAULT_PLAYBOOK,
    DEFAULT_TEMPLATES,
    analyze_document,
    bullet_list,
    compact_snippet,
    load_review_results,
    load_template_data,
    portable_clause_sections,
    portable_issue_rows,
    render_markdown_template,
    summarize_results,
)
from load_playbook import parse_playbook  # noqa: E402


DEFAULT_CLAUSE_NAMES = [
    "Data Protection",
    "Term and Termination",
    "Governing Law",
    "Dispute Resolution",
    "NDA Mutuality",
    "NDA Term",
    "NDA Carveouts",
]

FALLBACK_TEXT = "자료 부족—보류"


def parse_clause_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_profile(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def resolve_clause_profile(playbook_path: str, profile: str) -> tuple[list[str], str]:
    path = Path(playbook_path)
    if not path.exists():
        fallback_profile = normalize_profile(profile) or "default"
        return DEFAULT_CLAUSE_NAMES, fallback_profile

    playbook = parse_playbook(path)
    metadata = playbook.get("metadata", {})

    requested_profile = normalize_profile(profile)
    if not requested_profile or requested_profile == "auto":
        requested_profile = normalize_profile(metadata.get("compliance_profile")) or "default"

    candidate_keys: list[str] = []
    if requested_profile and requested_profile != "default":
        candidate_keys.append(f"compliance_clauses_{requested_profile}")
    candidate_keys.append("compliance_clauses")

    for key in candidate_keys:
        value = metadata.get(key)
        if value:
            return parse_clause_csv(value), requested_profile

    return DEFAULT_CLAUSE_NAMES, requested_profile


def filter_results(results: list[dict], clause_names: list[str]) -> list[dict]:
    wanted = {name.casefold() for name in clause_names}
    return [item for item in results if item.get("clause", "").casefold() in wanted]


def required_actions(results: list[dict], defaults: dict[str, str]) -> str:
    action_map = {
        "RED": defaults.get("required_action_red", "즉시 에스컬레이션 필요"),
        "YELLOW": defaults.get("required_action_yellow", "원문 보강 또는 재확인 필요"),
        "GREEN": defaults.get("required_action_green", "현재 기준 추가 조치 불요"),
    }
    lines = []
    for item in results:
        trigger = item.get("trigger_hit") or "-"
        lines.append(f"{item['clause']}: {action_map[item['status']]} | trigger: {trigger}")
    return bullet_list(lines, FALLBACK_TEXT)


def next_steps(results: list[dict], defaults: dict[str, str]) -> str:
    lines = []
    if any(item["status"] == "RED" for item in results):
        lines.append(defaults.get("escalation_note", "RED 항목은 내부 확인이 필요합니다."))
    if any(item["status"] == "YELLOW" for item in results):
        lines.append("YELLOW 항목은 원문과 배경사실을 다시 대조합니다.")
    if all(item["status"] == "GREEN" for item in results):
        lines.append("현재 확인 범위에서는 주요 컴플라이언스 리스크가 드러나지 않았습니다.")
    return bullet_list(lines, FALLBACK_TEXT)


def compliance_summary(
    input_name: str,
    overall: str,
    counts_data: dict[str, int],
    scope: str,
    profile: str,
) -> str:
    return (
        f"`{input_name}` 컴플라이언스 점검 결과는 `{overall}`입니다. "
        f"범위는 `{scope}` / profile `{profile}`이고 GREEN {counts_data['GREEN']}건 "
        f"YELLOW {counts_data['YELLOW']}건 RED {counts_data['RED']}건입니다."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a compliance-focused legal report")
    parser.add_argument("input_path", nargs="?", help="Input document path")
    parser.add_argument("--text", help="Inline document text")
    parser.add_argument("--review-path", help="Existing legal review report path")
    parser.add_argument("--playbook", default=str(DEFAULT_PLAYBOOK), help="Playbook path")
    parser.add_argument("--templates", default=str(DEFAULT_TEMPLATES), help="Template source path")
    parser.add_argument("--owner", default="미상", help="Compliance owner")
    parser.add_argument("--system", default="미상", help="Covered system or process")
    parser.add_argument("--scope", default="auto", help="Compliance scope label")
    parser.add_argument("--profile", default="auto", help="Compliance clause profile")
    parser.add_argument("--output", "-o", help="Output markdown path")
    args = parser.parse_args()

    clause_names, resolved_profile = resolve_clause_profile(args.playbook, args.profile)
    scope_label = args.scope if args.scope != "auto" else f"profile:{resolved_profile}"

    if args.review_path:
        analysis = load_review_results(args.review_path)
    else:
        analysis = analyze_document(
            args.input_path,
            args.text,
            args.playbook,
            clause_names=clause_names,
        )

    template_data, template_source = load_template_data(args.templates)
    defaults = template_data["sections"].get("compliance_defaults", {}).get("fields", {})
    results = filter_results(analysis["results"], clause_names)
    if not results:
        results = analysis["results"]
    summary_data = summarize_results(results)

    variables = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input_name": analysis["input_name"],
        "playbook_source": analysis["playbook_source"],
        "template_source": template_source,
        "owner": args.owner,
        "system": args.system,
        "scope": scope_label,
        "summary": compliance_summary(
            analysis["input_name"],
            summary_data["overall"],
            summary_data["counts"],
            scope_label,
            resolved_profile,
        ),
        "overall_status": summary_data["overall"],
        "green_count": str(summary_data["counts"]["GREEN"]),
        "yellow_count": str(summary_data["counts"]["YELLOW"]),
        "red_count": str(summary_data["counts"]["RED"]),
        "issues_table": portable_issue_rows(results),
        "required_actions": required_actions(results, defaults),
        "clause_sections": portable_clause_sections(results),
        "next_steps": next_steps(results, defaults),
        "evidence_note": bullet_list(
            [f"{item['clause']}: \"{compact_snippet(item['evidence'])}\"" for item in results],
            FALLBACK_TEXT,
        ),
        "disclaimer": "컴플라이언스 점검 초안이며 최종 확인이나 대외 발신 전에는 해당 법무 검토가 필요합니다.",
    }

    template_path = ROOT / ".agent" / "skills" / "legal-compliance" / "templates" / "compliance_review.md"
    output = render_markdown_template(template_path, variables)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"보고서가 저장됨: {output_path}")
    else:
        print(output)


if __name__ == "__main__":
    main()
