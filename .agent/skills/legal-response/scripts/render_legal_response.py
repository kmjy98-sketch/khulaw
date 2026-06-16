#!/usr/bin/env python3
"""Render a templated legal response draft."""

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
    focus_results,
    load_review_results,
    load_template_data,
    portable_issue_rows,
    render_markdown_template,
    safe_format,
)


def selected_results(results: list[dict], posture: str) -> list[dict]:
    if posture == "accept":
        accepted = [item for item in results if item["status"] == "GREEN"]
        return accepted or results
    return focus_results(results)


def draft_body(results: list[dict], posture_template: dict[str, str], posture: str) -> str:
    lines = [posture_template.get("opener", "검토 결과를 아래와 같이 정리합니다.")]
    for item in results:
        values = {
            "clause": item["clause"],
            "status": item["status"],
            "standard_position": item.get("standard_position") or "소스에서 확인할 수 없습니다",
            "trigger": item.get("trigger_hit") or "없음",
            "evidence": compact_snippet(item.get("evidence", "자료 부족—보류"), 160),
            "redline_suggestion": item.get("redline_suggestion") or "소스에서 확인할 수 없습니다",
            "fallback_position": item.get("fallback_position") or "소스에서 확인할 수 없습니다",
            "business_impact": item.get("business_impact") or "소스에서 확인할 수 없습니다",
        }
        clause_line = posture_template.get("clause_line", "{clause}: {status}")
        action_line = posture_template.get("action_line", "")
        lines.append("")
        lines.append(safe_format(clause_line, **values))
        if action_line:
            lines.append(safe_format(action_line, **values))
        if posture != "accept":
            lines.append(f"Suggested redline: {values['redline_suggestion']}")
            lines.append(f"Fallback: {values['fallback_position']}")
    close = posture_template.get("close")
    if close:
        lines.extend(["", close])
    return "\n".join(lines)


def internal_notes(results: list[dict], disclaimer: str) -> str:
    lines = [disclaimer]
    for item in results:
        lines.append(
            f"{item['clause']}: status={item['status']} / trigger={item.get('trigger_hit') or '-'} / "
            f"redline={compact_snippet(item.get('redline_suggestion', '자료 부족—보류'), 100)} / "
            f"impact={compact_snippet(item.get('business_impact', '자료 부족—보류'), 100)}"
        )
    return bullet_list(lines, "자료 부족—보류")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a legal response draft")
    parser.add_argument("input_path", nargs="?", help="Input document path")
    parser.add_argument("--text", help="Inline document text")
    parser.add_argument("--review-path", help="Existing legal review report path")
    parser.add_argument("--playbook", default=str(DEFAULT_PLAYBOOK), help="Playbook path")
    parser.add_argument("--templates", default=str(DEFAULT_TEMPLATES), help="Template source path")
    parser.add_argument("--recipient", default="상대방", help="Recipient label")
    parser.add_argument("--sender-role", default="법무", help="Sender role")
    parser.add_argument(
        "--posture",
        default="pushback",
        choices=["pushback", "clarify", "accept"],
        help="Draft posture",
    )
    parser.add_argument("--output", "-o", help="Output markdown path")
    args = parser.parse_args()

    if args.review_path:
        analysis = load_review_results(args.review_path)
    else:
        analysis = analyze_document(args.input_path, args.text, args.playbook)

    template_data, template_source = load_template_data(args.templates)
    defaults = template_data["sections"].get("response_defaults", {}).get("fields", {})
    posture_template = template_data["sections"].get("response_defaults", {}).get("templates", {}).get(args.posture, {})
    results = selected_results(analysis["results"], args.posture)

    variables = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input_name": analysis["input_name"],
        "playbook_source": analysis["playbook_source"],
        "template_source": template_source,
        "recipient": args.recipient,
        "sender_role": args.sender_role,
        "posture": args.posture,
        "overall_status": analysis["overall"],
        "draft_body": draft_body(results, posture_template, args.posture),
        "issues_table": portable_issue_rows(results),
        "internal_notes": internal_notes(results, defaults.get("external_disclaimer", "내부 확인 후 사용")),
        "disclaimer": "회신 초안이고 내부 확인 전에 발신하지 않는 문안입니다.",
    }

    template_path = ROOT / ".agent" / "skills" / "legal-response" / "templates" / "legal_response.md"
    output = render_markdown_template(template_path, variables)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"회신 초안 저장됨: {output_path}")
    else:
        print(output)


if __name__ == "__main__":
    main()
