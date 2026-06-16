#!/usr/bin/env python3
"""Run the local legal suite as a dry-run pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[3]
STATE_DIR = ROOT / ".agent" / "state"
DEFAULT_OUTPUT_ROOT = ROOT / "tmp" / "legal_suite_dry_run"
DEFAULT_LOG_PATH = STATE_DIR / "legal_suite_dry_run_log.json"
DEFAULT_PLAYBOOK = STATE_DIR / "legal_playbook.md"
DEFAULT_TEMPLATES = STATE_DIR / "legal_templates.md"

REVIEW_SCRIPT = SCRIPT_DIR / "render_review.py"
PACKET_SCRIPT = SCRIPT_DIR / "build_socratic_packet.py"
LAW_EVIDENCE_SCRIPT = SCRIPT_DIR / "build_law_evidence.py"
COMPLIANCE_SCRIPT = ROOT / ".agent" / "skills" / "legal-compliance" / "scripts" / "render_compliance_review.py"
BRIEFING_SCRIPT = ROOT / ".agent" / "skills" / "legal-briefing" / "scripts" / "render_legal_briefing.py"
RESPONSE_SCRIPT = ROOT / ".agent" / "skills" / "legal-response" / "scripts" / "render_legal_response.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_socratic_packet import parse_report  # noqa: E402


DEFAULT_OPTIONS = {
    "mode": "contract-review",
    "party": "미상",
    "deadline": "미상",
    "focus": "미상",
    "deal_context": "미상",
    "owner": "법무",
    "system": "계약 검토",
    "scope": "auto",
    "compliance_profile": "auto",
    "audience": "내부 검토자",
    "meeting": "내부 협상 회의",
    "objective": "핵심 리스크 정리",
    "recipient": "상대방 법무",
    "sender_role": "법무",
    "posture": "pushback",
}

PRESETS: dict[str, dict[str, str]] = {
    "default": {},
    "vendor-saas": {
        "mode": "contract-review",
        "focus": "벤더 SaaS 리스크 확인",
        "deal_context": "벤더 SaaS 계약",
        "system": "벤더 SaaS 계약",
        "compliance_profile": "vendor_saas",
        "meeting": "벤더 협상 회의",
        "objective": "벤더 계약 핵심 리스크 정리",
        "recipient": "상대방 법무",
        "posture": "pushback",
    },
    "nda-inbound": {
        "mode": "nda-triage",
        "focus": "NDA 상호성 및 예외사유 확인",
        "deal_context": "NDA 검토",
        "system": "NDA 검토",
        "compliance_profile": "nda",
        "meeting": "NDA 검토 회의",
        "objective": "비밀유지 조항 쟁점 정리",
        "recipient": "상대방 담당자",
        "posture": "clarify",
    },
    "privacy-dpa": {
        "mode": "contract-review",
        "focus": "개인정보 이전 및 보안 리스크 확인",
        "deal_context": "DPA/개인정보 처리 계약",
        "system": "개인정보 처리 계약",
        "compliance_profile": "privacy",
        "meeting": "개인정보 검토 회의",
        "objective": "데이터 처리·이전 리스크 정리",
        "recipient": "상대방 개인정보 담당자",
        "posture": "pushback",
    },
}


def resolve_output_dir(explicit_output_dir: str | None) -> Path:
    if explicit_output_dir:
        return Path(explicit_output_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return DEFAULT_OUTPUT_ROOT / stamp


def artifact_info(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
    }


def run_step(step_name: str, command: list[str], expected_output: Path | None = None) -> dict[str, Any]:
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, *command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        check=False,
    )
    duration_seconds = round(time.perf_counter() - start, 3)
    output_info = artifact_info(expected_output) if expected_output else None
    success = completed.returncode == 0 and (expected_output is None or expected_output.exists())
    return {
        "step": step_name,
        "started_at": started_at,
        "duration_seconds": duration_seconds,
        "command": " ".join([sys.executable, *command]),
        "exit_code": completed.returncode,
        "status": "completed" if success else "failed",
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "output": output_info,
    }


def review_snapshot(review_path: Path) -> dict[str, Any]:
    if not review_path.exists():
        return {"available": False}
    parsed = parse_report(review_path.read_text(encoding="utf-8"))
    counts = {"GREEN": 0, "YELLOW": 0, "RED": 0}
    for clause in parsed.get("clauses", []):
        status = clause.get("status", "YELLOW")
        counts[status] = counts.get(status, 0) + 1
    return {
        "available": True,
        "input_name": parsed.get("input_name", review_path.name),
        "overall_status": parsed.get("overall_status", "YELLOW"),
        "counts": counts,
        "clause_count": len(parsed.get("clauses", [])),
    }


def packet_snapshot(packet_path: Path) -> dict[str, Any]:
    if not packet_path.exists():
        return {"available": False}
    data = json.loads(packet_path.read_text(encoding="utf-8"))
    return {
        "available": True,
        "overall_status": data.get("overall_status", "YELLOW"),
        "focus_clause_count": len(data.get("focus_clauses", [])),
        "question_count": len(data.get("questions", [])),
        "retrieval_query_count": len(data.get("retrieval_queries", [])),
    }


def load_existing_log(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    try:
        existing = json.loads(log_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(existing, dict) and isinstance(existing.get("runs"), list):
        return existing["runs"]
    if isinstance(existing, list):
        return existing
    return []


def build_source_args(input_path: str | None, inline_text: str | None) -> tuple[list[str], str]:
    if inline_text:
        return ["--text", inline_text], "inline-text"
    if input_path:
        return [input_path], input_path
    raise ValueError("Either input_path or --text is required.")


def resolve_option(args: argparse.Namespace, option_name: str) -> str:
    explicit = getattr(args, option_name)
    if explicit is not None:
        return explicit
    preset_value = PRESETS[args.preset].get(option_name)
    if preset_value is not None:
        return preset_value
    return DEFAULT_OPTIONS[option_name]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the legal suite as a dry-run pipeline")
    parser.add_argument("input_path", nargs="?", help="Input contract path")
    parser.add_argument("--text", help="Inline contract text")
    parser.add_argument("--preset", default="default", choices=sorted(PRESETS), help="Convenience preset")
    parser.add_argument(
        "--mode",
        default=None,
        choices=["contract-review", "nda-triage"],
        help="Initial review mode",
    )
    parser.add_argument("--playbook", default=str(DEFAULT_PLAYBOOK), help="Playbook path")
    parser.add_argument("--templates", default=str(DEFAULT_TEMPLATES), help="Template path")
    parser.add_argument("--output-dir", help="Artifact output directory")
    parser.add_argument("--log-path", default=str(DEFAULT_LOG_PATH), help="Dry-run log path")
    parser.add_argument("--party", default=None, help="Review party label")
    parser.add_argument("--deadline", default=None, help="Review deadline label")
    parser.add_argument("--focus", default=None, help="Review focus label")
    parser.add_argument("--deal-context", default=None, help="Deal context label")
    parser.add_argument("--owner", default=None, help="Compliance owner")
    parser.add_argument("--system", default=None, help="Covered system or process")
    parser.add_argument("--scope", default=None, help="Compliance scope")
    parser.add_argument("--compliance-profile", default=None, help="Compliance clause profile")
    parser.add_argument("--audience", default=None, help="Briefing audience")
    parser.add_argument("--meeting", default=None, help="Briefing meeting title")
    parser.add_argument("--objective", default=None, help="Briefing objective")
    parser.add_argument("--recipient", default=None, help="Response recipient")
    parser.add_argument("--sender-role", default=None, help="Response sender role")
    parser.add_argument(
        "--posture",
        default=None,
        choices=["pushback", "clarify", "accept"],
        help="Response posture",
    )
    args = parser.parse_args()

    resolved = {
        "mode": resolve_option(args, "mode"),
        "party": resolve_option(args, "party"),
        "deadline": resolve_option(args, "deadline"),
        "focus": resolve_option(args, "focus"),
        "deal_context": resolve_option(args, "deal_context"),
        "owner": resolve_option(args, "owner"),
        "system": resolve_option(args, "system"),
        "scope": resolve_option(args, "scope"),
        "compliance_profile": resolve_option(args, "compliance_profile"),
        "audience": resolve_option(args, "audience"),
        "meeting": resolve_option(args, "meeting"),
        "objective": resolve_option(args, "objective"),
        "recipient": resolve_option(args, "recipient"),
        "sender_role": resolve_option(args, "sender_role"),
        "posture": resolve_option(args, "posture"),
    }

    source_args, source_name = build_source_args(args.input_path, args.text)
    output_dir = resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    review_path = output_dir / "legal_review.md"
    compliance_path = output_dir / "legal_compliance.md"
    briefing_path = output_dir / "legal_briefing.md"
    response_path = output_dir / "legal_response.md"
    packet_path = output_dir / "legal_socratic_packet.json"
    law_evidence_path = output_dir / "legal_law_evidence.json"

    review_command = [
        str(REVIEW_SCRIPT),
        *source_args,
        "--mode",
        resolved["mode"],
        "--playbook",
        args.playbook,
        "--party",
        resolved["party"],
        "--deadline",
        resolved["deadline"],
        "--focus",
        resolved["focus"],
        "--deal-context",
        resolved["deal_context"],
        "--output",
        str(review_path),
    ]

    compliance_command = [
        str(COMPLIANCE_SCRIPT),
        "--review-path",
        str(review_path),
        "--playbook",
        args.playbook,
        "--templates",
        args.templates,
        "--owner",
        resolved["owner"],
        "--system",
        resolved["system"],
        "--scope",
        resolved["scope"],
        "--profile",
        resolved["compliance_profile"],
        "--output",
        str(compliance_path),
    ]

    briefing_command = [
        str(BRIEFING_SCRIPT),
        "--review-path",
        str(review_path),
        "--playbook",
        args.playbook,
        "--templates",
        args.templates,
        "--audience",
        resolved["audience"],
        "--meeting",
        resolved["meeting"],
        "--objective",
        resolved["objective"],
        "--output",
        str(briefing_path),
    ]

    response_command = [
        str(RESPONSE_SCRIPT),
        "--review-path",
        str(review_path),
        "--playbook",
        args.playbook,
        "--templates",
        args.templates,
        "--recipient",
        resolved["recipient"],
        "--sender-role",
        resolved["sender_role"],
        "--posture",
        resolved["posture"],
        "--output",
        str(response_path),
    ]

    packet_command = [
        str(PACKET_SCRIPT),
        str(review_path),
        "--output",
        str(packet_path),
    ]

    law_evidence_command = [
        str(LAW_EVIDENCE_SCRIPT),
        str(review_path),
        "--output",
        str(law_evidence_path),
    ]

    # (step_name, command, expected_output, required)
    # required=False → 실패해도 전체 파이프라인 실패로 처리하지 않음
    step_specs: list[tuple[str, list[str], Path, bool]] = [
        ("legal-review", review_command, review_path, True),
        ("legal-compliance", compliance_command, compliance_path, True),
        ("legal-briefing", briefing_command, briefing_path, True),
        ("legal-response", response_command, response_path, True),
        ("legal-socratic-packet", packet_command, packet_path, True),
        ("korean-law-evidence", law_evidence_command, law_evidence_path, False),
    ]

    steps: list[dict[str, Any]] = []
    required_failed = False
    for step_name, command, expected_output, required in step_specs:
        if required_failed and required:
            steps.append(
                {
                    "step": step_name,
                    "status": "skipped",
                    "reason": f"Previous required step failed",
                    "output": artifact_info(expected_output),
                }
            )
            continue
        result = run_step(step_name, command, expected_output)
        if not required and result["status"] == "failed":
            result["optional"] = True
            result["status"] = "optional_failed"
        elif required and result["status"] == "failed":
            required_failed = True
        steps.append(result)

    run_status = "completed" if all(
        s["status"] in ("completed", "optional_failed") for s in steps
        if s["status"] != "skipped"
    ) else "failed"
    run_entry = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "preset": args.preset,
        "mode": resolved["mode"],
        "status": run_status,
        "source_name": source_name,
        "resolved_options": resolved,
        "output_dir": str(output_dir),
        "artifacts": {
            "review": artifact_info(review_path),
            "compliance": artifact_info(compliance_path),
            "briefing": artifact_info(briefing_path),
            "response": artifact_info(response_path),
            "packet": artifact_info(packet_path),
            "law_evidence": artifact_info(law_evidence_path),
        },
        "review_summary": review_snapshot(review_path),
        "packet_summary": packet_snapshot(packet_path),
        "steps": steps,
    }

    log_path = Path(args.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    history = load_existing_log(log_path)
    history.append(run_entry)
    payload = {
        "log_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latest_status": run_status,
        "runs": history,
    }
    log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Dry-run status: {run_status}")
    print(f"Preset: {args.preset}")
    print(f"Artifacts: {output_dir}")
    print(f"Log: {log_path}")

    if run_status != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
