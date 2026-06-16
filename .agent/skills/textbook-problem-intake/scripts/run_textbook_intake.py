#!/usr/bin/env python3
"""Run the textbook problem intake pipeline end to end."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[4]
STATE_DIR = ROOT / ".agent" / "state"
DEFAULT_EXTRACT_DIR = ROOT / ".agent" / "data" / "pdf_extracts"
DEFAULT_SCAN_OUTPUT = STATE_DIR / "textbook_problem_candidates.json"
DEFAULT_SCAN_LOG = STATE_DIR / "textbook_problem_scan_log.json"
DEFAULT_REGISTER_LOG = STATE_DIR / "textbook_problem_register_log.json"
DEFAULT_PIPELINE_LOG = STATE_DIR / "textbook_problem_pipeline_log.json"

PDF_INGEST_SCRIPT = ROOT / ".agent" / "skills" / "pdf-ingest" / "scripts" / "ingest.py"
SCAN_SCRIPT = ROOT / ".agent" / "skills" / "problem-index" / "scripts" / "scan_textbook_embedded_problems.py"
REGISTER_SCRIPT = ROOT / ".agent" / "skills" / "problem-index" / "scripts" / "register_textbook_problem_candidates.py"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def run_step(command: list[str], workdir: Path) -> dict[str, Any]:
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    completed = subprocess.run(
        command,
        cwd=str(workdir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "command": command,
        "started_at": started_at,
        "finished_at": finished_at,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def summarize_outputs(scan_output: Path, scan_log: Path, register_log: Path) -> dict[str, Any]:
    manifest = load_json(scan_output, {})
    scan_summary = load_json(scan_log, {})
    register_summary = load_json(register_log, {})
    return {
        "candidate_manifest": {
            "path": str(scan_output),
            "candidate_count": manifest.get("candidate_count", 0),
        },
        "scan_log": {
            "path": str(scan_log),
            "sources": scan_summary.get("totals", {}).get("sources", 0),
            "chunks": scan_summary.get("totals", {}).get("chunks", 0),
            "candidates": scan_summary.get("totals", {}).get("candidates", 0),
            "pending_db_registration": scan_summary.get("totals", {}).get("pending_db_registration", 0),
            "pending_topic_mapping": scan_summary.get("totals", {}).get("pending_topic_mapping", 0),
        },
        "register_log": {
            "path": str(register_log),
            "selected_candidates": register_summary.get("selected_candidates", 0),
            "registered": len(register_summary.get("registered", [])),
            "skipped": len(register_summary.get("skipped", [])),
            "apply": register_summary.get("apply", False),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run textbook intake: extract -> scan -> register")
    parser.add_argument("--subject", help="Limit intake to one subject")
    parser.add_argument("--pdf-dir", help="PDF directory to extract before scanning")
    parser.add_argument("--extract-dir", default=str(DEFAULT_EXTRACT_DIR), help="Markdown extract directory")
    parser.add_argument("--pattern", default="**/*.pdf", help="PDF glob pattern for extraction")
    parser.add_argument("--chunk-size", type=int, default=30, help="Chunk size for extraction")
    parser.add_argument("--skip-extract", action="store_true", help="Use existing extracts only")
    parser.add_argument("--skip-register", action="store_true", help="Skip register dry-run/apply step")
    parser.add_argument("--apply", action="store_true", help="Apply textbook registrations to problem_index.json")
    parser.add_argument("--scan-output", default=str(DEFAULT_SCAN_OUTPUT), help="Candidate manifest path")
    parser.add_argument("--scan-log-output", default=str(DEFAULT_SCAN_LOG), help="Scan log path")
    parser.add_argument("--register-log-output", default=str(DEFAULT_REGISTER_LOG), help="Register log path")
    parser.add_argument("--pipeline-log-output", default=str(DEFAULT_PIPELINE_LOG), help="Pipeline log path")
    args = parser.parse_args()

    extract_dir = Path(args.extract_dir)
    scan_output = Path(args.scan_output)
    scan_log_output = Path(args.scan_log_output)
    register_log_output = Path(args.register_log_output)
    pipeline_log_output = Path(args.pipeline_log_output)

    pipeline_log: dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "subject": args.subject or "all",
        "mode": {
            "skip_extract": args.skip_extract,
            "skip_register": args.skip_register,
            "apply": args.apply,
        },
        "paths": {
            "pdf_dir": args.pdf_dir or "",
            "extract_dir": str(extract_dir),
            "scan_output": str(scan_output),
            "scan_log_output": str(scan_log_output),
            "register_log_output": str(register_log_output),
        },
        "steps": [],
        "outputs": {},
    }

    if not args.skip_extract:
        if not args.pdf_dir:
            raise SystemExit("--pdf-dir is required unless --skip-extract is used")
        extract_command = [
            sys.executable,
            str(PDF_INGEST_SCRIPT),
            "--pdf-dir",
            args.pdf_dir,
            "--out",
            str(extract_dir),
            "--pattern",
            args.pattern,
            "--chunk-size",
            str(args.chunk_size),
            "--extract-only",
        ]
        extract_result = run_step(extract_command, ROOT)
        extract_result["name"] = "extract"
        pipeline_log["steps"].append(extract_result)
        if extract_result["returncode"] != 0:
            pipeline_log_output.parent.mkdir(parents=True, exist_ok=True)
            pipeline_log_output.write_text(json.dumps(pipeline_log, ensure_ascii=False, indent=2), encoding="utf-8")
            raise SystemExit("extract step failed")

    scan_command = [
        sys.executable,
        str(SCAN_SCRIPT),
        "--output",
        str(scan_output),
        "--log-output",
        str(scan_log_output),
    ]
    if args.subject:
        scan_command.extend(["--subject", args.subject])
    scan_result = run_step(scan_command, ROOT)
    scan_result["name"] = "scan"
    pipeline_log["steps"].append(scan_result)
    if scan_result["returncode"] != 0:
        pipeline_log_output.parent.mkdir(parents=True, exist_ok=True)
        pipeline_log_output.write_text(json.dumps(pipeline_log, ensure_ascii=False, indent=2), encoding="utf-8")
        raise SystemExit("scan step failed")

    if not args.skip_register:
        register_command = [
            sys.executable,
            str(REGISTER_SCRIPT),
            "--input",
            str(scan_output),
            "--log-output",
            str(register_log_output),
        ]
        if args.subject:
            register_command.extend(["--subject", args.subject])
        if args.apply:
            register_command.append("--apply")
        register_result = run_step(register_command, ROOT)
        register_result["name"] = "register"
        pipeline_log["steps"].append(register_result)
        if register_result["returncode"] != 0:
            pipeline_log_output.parent.mkdir(parents=True, exist_ok=True)
            pipeline_log_output.write_text(json.dumps(pipeline_log, ensure_ascii=False, indent=2), encoding="utf-8")
            raise SystemExit("register step failed")

    pipeline_log["outputs"] = summarize_outputs(scan_output, scan_log_output, register_log_output)
    pipeline_log_output.parent.mkdir(parents=True, exist_ok=True)
    pipeline_log_output.write_text(json.dumps(pipeline_log, ensure_ascii=False, indent=2), encoding="utf-8")

    outputs = pipeline_log["outputs"]
    print(f"candidate_count={outputs['candidate_manifest']['candidate_count']}")
    print(f"pending_db_registration={outputs['scan_log']['pending_db_registration']}")
    print(f"pending_topic_mapping={outputs['scan_log']['pending_topic_mapping']}")
    if not args.skip_register:
        print(f"register_selected={outputs['register_log']['selected_candidates']}")
        print(f"register_ready={outputs['register_log']['registered']}")
        print(f"register_skipped={outputs['register_log']['skipped']}")
    print(f"pipeline_log={pipeline_log_output}")


if __name__ == "__main__":
    main()
