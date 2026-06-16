#!/usr/bin/env python3
"""Run venue/governing-law regression cases through the local legal suite."""

from __future__ import annotations

import argparse
import json
import re
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
DEFAULT_CASES_PATH = STATE_DIR / "legal_venue_regression_cases.json"
DEFAULT_LOG_PATH = STATE_DIR / "legal_venue_regression_log.json"
DEFAULT_OUTPUT_ROOT = ROOT / "tmp" / "legal_suite_regression"
SUITE_SCRIPT = SCRIPT_DIR / "run_legal_suite.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_socratic_packet import parse_report  # noqa: E402


def sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._-") or "case"


def ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        cases = data.get("cases", [])
    elif isinstance(data, list):
        cases = data
    else:
        cases = []
    if not isinstance(cases, list):
        raise ValueError("Regression case file must contain a list of cases.")
    return [case for case in cases if isinstance(case, dict)]


def evaluate_expectations(case: dict[str, Any], review_path: Path) -> dict[str, Any]:
    parsed = parse_report(review_path.read_text(encoding="utf-8"))
    by_clause = {item.get("clause", ""): item for item in parsed.get("clauses", [])}
    checks: list[dict[str, Any]] = []

    for expected in case.get("expectations", []):
        clause_name = str(expected.get("clause", ""))
        observed = by_clause.get(clause_name)
        reasons: list[str] = []
        passed = True

        if observed is None:
            passed = False
            reasons.append("missing clause")
            checks.append(
                {
                    "clause": clause_name,
                    "passed": passed,
                    "expected": expected,
                    "observed": None,
                    "reasons": reasons,
                }
            )
            continue

        expected_status = expected.get("status")
        if expected_status and observed.get("status") != expected_status:
            passed = False
            reasons.append(f"status mismatch: expected {expected_status}, got {observed.get('status')}")

        trigger_hit = str(observed.get("trigger_hit", ""))
        for fragment in ensure_list(expected.get("trigger_contains")):
            if fragment.lower() not in trigger_hit.lower():
                passed = False
                reasons.append(f"trigger mismatch: expected fragment `{fragment}` in `{trigger_hit}`")

        matched_term = str(observed.get("matched_term", ""))
        for fragment in ensure_list(expected.get("matched_contains")):
            if fragment.lower() not in matched_term.lower():
                passed = False
                reasons.append(f"matched term mismatch: expected fragment `{fragment}` in `{matched_term}`")

        checks.append(
            {
                "clause": clause_name,
                "passed": passed,
                "expected": expected,
                "observed": {
                    "status": observed.get("status", ""),
                    "matched_term": matched_term,
                    "trigger_hit": trigger_hit,
                },
                "reasons": reasons,
            }
        )

    return {
        "overall_status": parsed.get("overall_status", "YELLOW"),
        "checks": checks,
        "passed": all(check.get("passed", False) for check in checks) if checks else True,
    }


def run_case(case: dict[str, Any], output_root: Path) -> dict[str, Any]:
    case_id = str(case.get("id", "case"))
    preset = str(case.get("preset", "vendor-saas"))
    case_output_dir = output_root / sanitize_name(case_id)
    case_output_dir.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        str(SUITE_SCRIPT),
        "--preset",
        preset,
        "--output-dir",
        str(case_output_dir),
        "--text",
        str(case.get("text", "")),
    ]

    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start = time.perf_counter()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        check=False,
    )
    duration_seconds = round(time.perf_counter() - start, 3)

    review_path = case_output_dir / "legal_review.md"
    evaluation = None
    status = "completed" if completed.returncode == 0 and review_path.exists() else "failed"
    if status == "completed":
        evaluation = evaluate_expectations(case, review_path)
        if not evaluation["passed"]:
            status = "failed"

    return {
        "id": case_id,
        "preset": preset,
        "started_at": started_at,
        "duration_seconds": duration_seconds,
        "status": status,
        "output_dir": str(case_output_dir),
        "review_path": str(review_path),
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "evaluation": evaluation,
    }


def load_existing_runs(log_path: Path) -> list[dict[str, Any]]:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run legal venue regression cases")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Regression case JSON path")
    parser.add_argument("--log-path", default=str(DEFAULT_LOG_PATH), help="Regression log JSON path")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Regression artifact root")
    args = parser.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.exists():
        raise FileNotFoundError(f"Regression case file not found: {cases_path}")

    cases = load_cases(cases_path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_root = Path(args.output_root) / stamp
    output_root.mkdir(parents=True, exist_ok=True)

    case_results = [run_case(case, output_root) for case in cases]
    passed_cases = sum(1 for item in case_results if item.get("status") == "completed")
    failed_cases = len(case_results) - passed_cases
    run_status = "completed" if failed_cases == 0 else "failed"

    run_record = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": run_status,
        "cases_path": str(cases_path),
        "artifact_root": str(output_root),
        "total_cases": len(case_results),
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "cases": case_results,
    }

    log_path = Path(args.log_path)
    existing_runs = load_existing_runs(log_path)
    existing_runs.append(run_record)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        json.dumps(
            {
                "latest_status": run_status,
                "latest_generated_at": run_record["generated_at"],
                "runs": existing_runs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Regression status: {run_status}")
    print(f"Cases: {passed_cases}/{len(case_results)} passed")
    print(f"Artifacts: {output_root}")
    print(f"Log: {log_path}")

    if failed_cases:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
