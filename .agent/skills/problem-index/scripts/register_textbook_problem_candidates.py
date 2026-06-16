#!/usr/bin/env python3
"""Register scanned textbook problem candidates into problem_index.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[4]
STATE_DIR = ROOT / ".agent" / "state"
PROBLEM_INDEX_PATH = STATE_DIR / "problem_index.json"
DEFAULT_INPUT = STATE_DIR / "textbook_problem_candidates.json"
DEFAULT_LOG = STATE_DIR / "textbook_problem_register_log.json"

CHOICE_RE = re.compile(r"([①②③④⑤])\s*([^①②③④⑤]+)")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_excerpt(text: str, limit: int = 120) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."


def extract_choices(text: str) -> list[str]:
    choices: list[str] = []
    for _, raw_choice in CHOICE_RE.findall(text):
        choice = normalize_text(raw_choice)
        if choice:
            choices.append(choice)
        if len(choices) >= 5:
            break
    return choices


def build_problem_signature(item: dict[str, Any]) -> tuple[str, int | str, str]:
    source_ref = str(
        item.get("source_pdf")
        or item.get("file")
        or item.get("source_md")
        or ""
    ).strip()
    page = item.get("page")
    if isinstance(page, int):
        page_value: int | str = page
    else:
        try:
            page_value = int(page)
        except (TypeError, ValueError):
            page_value = ""
    return source_ref, page_value, normalize_text(item.get("question_text", ""))


def build_textbook_entry(candidate: dict[str, Any], manifest_source: str) -> dict[str, Any]:
    question_text = normalize_text(candidate.get("question_text", ""))
    problem_type = candidate.get("problem_type", "unknown")
    choices = extract_choices(question_text)

    entry: dict[str, Any] = {
        "id": candidate.get("id"),
        "file": candidate.get("source_pdf", "미상"),
        "source_pdf": candidate.get("source_pdf", "미상"),
        "source_md": candidate.get("source_md"),
        "page": candidate.get("page"),
        "page_span_hint": candidate.get("page_span_hint"),
        "question_type": "choice" if problem_type == "objective" else problem_type,
        "problem_type": problem_type,
        "question_label": candidate.get("question_label", ""),
        "question_text": question_text,
        "question_preview": candidate.get("question_preview") or build_excerpt(question_text, 100),
        "answer": None,
        "answer_source": None,
        "verified": False,
        "signals": candidate.get("signals", []),
        "signal_score": candidate.get("signal_score"),
        "confidence": candidate.get("confidence"),
        "registration_status": "pending_review",
        "candidate_source": manifest_source,
    }
    if choices:
        entry["choices"] = choices
    return entry


def resolve_candidates(
    manifest: dict[str, Any],
    candidate_ids: set[str],
    subject_filter: str | None,
    topic_filter: str | None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for candidate in manifest.get("candidates", []):
        candidate_id = candidate.get("id", "")
        if candidate_ids and candidate_id not in candidate_ids:
            continue

        primary_topic = candidate.get("primary_topic") or {}
        if subject_filter and primary_topic.get("subject") != subject_filter:
            continue
        if topic_filter and primary_topic.get("topic") != topic_filter:
            continue
        selected.append(candidate)
    return selected


def build_subject_textbook_indexes(problem_index: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, set[tuple[str, int | str, str]]]]:
    ids_by_subject: dict[str, set[str]] = {}
    signatures_by_subject: dict[str, set[tuple[str, int | str, str]]] = {}

    for subject_name, subject_data in problem_index.get("subjects", {}).items():
        subject_ids: set[str] = set()
        subject_signatures: set[tuple[str, int | str, str]] = set()
        for topic_data in subject_data.get("topics", {}).values():
            textbook_items = (topic_data.get("problems", {}) or {}).get("textbook", []) or []
            for item in textbook_items:
                if not isinstance(item, dict):
                    continue
                item_id = item.get("id")
                if item_id:
                    subject_ids.add(item_id)
                subject_signatures.add(build_problem_signature(item))
        ids_by_subject[subject_name] = subject_ids
        signatures_by_subject[subject_name] = subject_signatures

    return ids_by_subject, signatures_by_subject


def main() -> None:
    parser = argparse.ArgumentParser(description="Register textbook problem candidates into problem_index.json")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Candidate manifest JSON path")
    parser.add_argument("--log-output", default=str(DEFAULT_LOG), help="Registration log JSON path")
    parser.add_argument("--subject", help="Limit registration to one subject")
    parser.add_argument("--topic", help="Limit registration to one topic")
    parser.add_argument("--candidate-id", action="append", default=[], help="Register only selected candidate ids")
    parser.add_argument("--apply", action="store_true", help="Write changes to problem_index.json")
    args = parser.parse_args()

    manifest_path = Path(args.input)
    manifest = load_json(manifest_path, {})
    problem_index = load_json(PROBLEM_INDEX_PATH, {})
    candidate_ids = set(args.candidate_id or [])
    candidates = resolve_candidates(manifest, candidate_ids, args.subject, args.topic)
    subject_existing_ids, subject_existing_signatures = build_subject_textbook_indexes(problem_index)

    log: dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input": str(manifest_path),
        "apply": args.apply,
        "subject_filter": args.subject or "all",
        "topic_filter": args.topic or "all",
        "selected_candidates": len(candidates),
        "registered": [],
        "skipped": [],
    }

    for candidate in candidates:
        candidate_id = candidate.get("id", "unknown")
        primary_topic = candidate.get("primary_topic") or {}
        subject_name = primary_topic.get("subject")
        topic_name = primary_topic.get("topic")
        status = candidate.get("status")

        if status != "pending_db_registration":
            log["skipped"].append({"id": candidate_id, "reason": f"status={status}"})
            continue
        if not subject_name or not topic_name:
            log["skipped"].append({"id": candidate_id, "reason": "primary_topic_missing"})
            continue

        subject_data = problem_index.get("subjects", {}).get(subject_name)
        if not isinstance(subject_data, dict):
            log["skipped"].append({"id": candidate_id, "reason": f"subject_missing={subject_name}"})
            continue

        topic_data = subject_data.get("topics", {}).get(topic_name)
        if not isinstance(topic_data, dict):
            log["skipped"].append({"id": candidate_id, "reason": f"topic_missing={topic_name}"})
            continue

        problems = topic_data.setdefault("problems", {})
        textbook_items = problems.setdefault("textbook", [])
        existing_ids = subject_existing_ids.setdefault(subject_name, set())
        existing_signatures = subject_existing_signatures.setdefault(subject_name, set())
        if candidate_id in existing_ids:
            log["skipped"].append({"id": candidate_id, "reason": "duplicate"})
            continue

        candidate_signature = build_problem_signature(candidate)
        if candidate_signature in existing_signatures:
            log["skipped"].append({"id": candidate_id, "reason": "duplicate_signature"})
            continue

        entry = build_textbook_entry(candidate, str(manifest_path))
        if args.apply:
            textbook_items.append(entry)
            topic_data["problems"] = problems
        existing_ids.add(candidate_id)
        existing_signatures.add(candidate_signature)

        log["registered"].append(
            {
                "id": candidate_id,
                "subject": subject_name,
                "topic": topic_name,
                "file": candidate.get("source_pdf", "미상"),
                "page": candidate.get("page"),
                "problem_type": candidate.get("problem_type", "unknown"),
            }
        )

    if args.apply:
        problem_index["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        PROBLEM_INDEX_PATH.write_text(json.dumps(problem_index, ensure_ascii=False, indent=2), encoding="utf-8")

    log_path = Path(args.log_output)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"등록 대상: {len(log['registered'])}개")
    print(f"건너뜀: {len(log['skipped'])}개")
    print(f"로그 저장: {log_path}")
    if args.apply:
        print(f"problem_index 저장: {PROBLEM_INDEX_PATH}")


if __name__ == "__main__":
    main()
