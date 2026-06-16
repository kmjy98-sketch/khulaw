#!/usr/bin/env python3
"""Render a meeting-style legal briefing memo."""

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
)


def executive_summary(analysis: dict, defaults: dict[str, str]) -> str:
    impact_key = f"impact_{analysis['overall'].lower()}"
    lines = [
        defaults.get("executive_summary_prefix", "아래 메모는 회의용 초안입니다."),
        f"Overall 상태는 {analysis['overall']}이고, RED {analysis['counts']['RED']}건 / YELLOW {analysis['counts']['YELLOW']}건 / GREEN {analysis['counts']['GREEN']}건입니다.",
        defaults.get(impact_key, "자료 부족—보류"),
    ]
    return bullet_list(lines, "자료 부족—보류")


def decision_points(results: list[dict], defaults: dict[str, str]) -> str:
    lines = []
    for item in results:
        if item["status"] == "RED":
            action = defaults.get("decision_request_red", "RED 항목 확인 여부 결정")
        elif item["status"] == "YELLOW":
            action = defaults.get("decision_request_yellow", "YELLOW 항목 추가 확인")
        else:
            action = defaults.get("impact_green", "현 기준과 직접 충돌 사항 없음")
        priority = item.get("negotiation_priority") or "monitor"
        lines.append(f"{item['clause']}: {action} / priority={priority}")
    return bullet_list(lines, "자료 부족—보류")


def clause_notes(results: list[dict]) -> str:
    blocks = []
    for item in results:
        lines = [
            f"### {item['clause']}",
            f"- 상태: {item['status']}",
            f"- 협상 우선순위: {item.get('negotiation_priority') or '소스에서 확인할 수 없습니다'}",
            f"- 트리거: {item.get('trigger_hit') or '없음'}",
            f"- 기준 요약: {item.get('standard_position') or '소스에서 확인할 수 없습니다'}",
            f"- redline 제안: {item.get('redline_suggestion') or '소스에서 확인할 수 없습니다'}",
            f"- fallback 포지션: {item.get('fallback_position') or '소스에서 확인할 수 없습니다'}",
            f"- business impact: {item.get('business_impact') or '소스에서 확인할 수 없습니다'}",
            f"- 근거 스니펫: \"{compact_snippet(item.get('evidence', '자료 부족—보류'), 180)}\"",
        ]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) if blocks else "- 자료 부족—보류"


def questions(results: list[dict], defaults: dict[str, str]) -> str:
    prefix = defaults.get("question_prefix", "확인 질문")
    lines = []
    for item in results:
        trigger = item.get("trigger_hit")
        if trigger and trigger != "없음":
            lines.append(f"{prefix}: {item['clause']} 조항에서 `{trigger}` 문구를 수용할지, redline으로 밀어낼지 결정이 필요한가.")
        else:
            lines.append(f"{prefix}: {item['clause']} 조항에 fallback 포지션을 적용해야 할 정도의 누락이 있는가.")
    return bullet_list(lines, "자료 부족—보류")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a legal briefing memo")
    parser.add_argument("input_path", nargs="?", help="Input document path")
    parser.add_argument("--text", help="Inline document text")
    parser.add_argument("--review-path", help="Existing legal review report path")
    parser.add_argument("--playbook", default=str(DEFAULT_PLAYBOOK), help="Playbook path")
    parser.add_argument("--templates", default=str(DEFAULT_TEMPLATES), help="Template source path")
    parser.add_argument("--audience", default="내부 검토자", help="Audience label")
    parser.add_argument("--meeting", default="미지정", help="Meeting or context")
    parser.add_argument("--objective", default="쟁점 정리", help="Briefing objective")
    parser.add_argument("--output", "-o", help="Output markdown path")
    args = parser.parse_args()

    if args.review_path:
        analysis = load_review_results(args.review_path)
    else:
        analysis = analyze_document(args.input_path, args.text, args.playbook)

    template_data, template_source = load_template_data(args.templates)
    defaults = template_data["sections"].get("briefing_defaults", {}).get("fields", {})
    results = focus_results(analysis["results"])

    variables = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input_name": analysis["input_name"],
        "playbook_source": analysis["playbook_source"],
        "template_source": template_source,
        "audience": args.audience,
        "meeting": args.meeting,
        "objective": args.objective,
        "overall_status": analysis["overall"],
        "executive_summary": executive_summary(analysis, defaults),
        "risk_snapshot": portable_issue_rows(results),
        "decision_points": decision_points(results, defaults),
        "clause_notes": clause_notes(results),
        "questions": questions(results, defaults),
        "disclaimer": "브리핑 메모 초안이고 최종 법률 의견이나 대외 회신 문안은 아닙니다.",
    }

    template_path = ROOT / ".agent" / "skills" / "legal-briefing" / "templates" / "legal_briefing.md"
    output = render_markdown_template(template_path, variables)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"브리핑 저장됨: {output_path}")
    else:
        print(output)


if __name__ == "__main__":
    main()
