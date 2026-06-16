#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rename transcript and correction files to ASCII aliases.

Scope:
- files under */전사문/
- processed transcript archives
- unmatched transcript folders

Excluded:
- note/summary files
- PDFs and non-text assets
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
STATE_DIR = ROOT / ".agent" / "state"
LOG_PATH = STATE_DIR / "transcription_log.json"
LIB_DIR = ROOT / ".agent" / "lib"

if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from transcript_naming import canonicalize_transcript_name


TARGET_ROOTS = [
    ROOT / "1.민사",
    ROOT / "2.형사",
    ROOT / "3.공법",
    ROOT / "4.선택법",
]
EXTRA_ROOTS = [
    ROOT / "5.기타" / "_inbox" / "녹음" / "processed" / "transcripts",
    ROOT / "5.기타" / "_inbox" / "녹음" / "unmatched_transcripts",
]
SKIP_NAME_TOKENS = ("정리", "노트", "요약", "chunks_index")


@dataclass
class RenamePlan:
    kind: str
    old_path: Path
    exec_target: Path
    final_target: Path
    reason: str


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def discover_transcript_roots() -> list[Path]:
    roots: list[Path] = []
    for parent in TARGET_ROOTS:
        if not parent.exists():
            continue
        roots.extend(path for path in parent.rglob("전사문") if path.is_dir())
    roots.extend(path for path in EXTRA_ROOTS if path.exists())
    unique = []
    seen = set()
    for path in roots:
        norm = str(path)
        if norm in seen:
            continue
        seen.add(norm)
        unique.append(path)
    return unique


def should_include_file(path: Path) -> bool:
    if path.suffix.lower() not in {".md", ".txt"}:
        return False
    return not any(token in path.name for token in SKIP_NAME_TOKENS)


def rewrite_path_text(text: str, mapping: dict[str, str]) -> str:
    if not text:
        return text
    updated = str(text)
    for old_path, new_path in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
        if updated == old_path:
            return new_path
        prefix = old_path + "\\"
        if updated.startswith(prefix):
            return new_path + updated[len(old_path) :]
    return updated


def build_directory_plans(transcript_roots: list[Path]) -> list[dict]:
    rows = []
    for root in transcript_roots:
        for path in sorted((candidate for candidate in root.rglob("*") if candidate.is_dir()), key=lambda item: len(item.parts)):
            info = canonicalize_transcript_name(ROOT, path.name, is_dir=True)
            if not info["matched"] or not info["changed"]:
                continue
            rows.append(
                {
                    "old_path": path,
                    "new_name": info["canonical_name"],
                    "canonical_stem": info["canonical_stem"],
                    "reason": f"{path.name} -> {info['canonical_name']}",
                }
            )
    return rows


def build_directory_maps(directory_rows: list[dict]) -> tuple[list[RenamePlan], dict[str, str], dict[str, str]]:
    ordered = sorted(directory_rows, key=lambda item: len(item["old_path"].parts))
    current_name_map: dict[str, str] = {}
    final_map: dict[str, str] = {}
    plans: list[RenamePlan] = []

    for row in ordered:
        old_path = row["old_path"]
        current_parent = Path(rewrite_path_text(str(old_path.parent), current_name_map))
        current_target = current_parent / row["new_name"]
        current_name_map[str(old_path)] = str(current_target)

        final_parent = Path(rewrite_path_text(str(old_path.parent), final_map))
        final_target = final_parent / row["new_name"]
        final_map[str(old_path)] = str(final_target)

        plans.append(
            RenamePlan(
                kind="dir",
                old_path=old_path,
                exec_target=current_target,
                final_target=final_target,
                reason=row["reason"],
            )
        )

    return plans, current_name_map, final_map


def session_stem_for_parent(parent: Path) -> str | None:
    info = canonicalize_transcript_name(ROOT, parent.name, is_dir=True)
    if info["matched"] and info["session_token"]:
        return info["canonical_stem"]
    return None


def build_file_plans(transcript_roots: list[Path], final_dir_map: dict[str, str]) -> list[RenamePlan]:
    plans: list[RenamePlan] = []

    for root in transcript_roots:
        for path in sorted((candidate for candidate in root.rglob("*") if candidate.is_file()), key=lambda item: (len(item.parts), item.name)):
            if not should_include_file(path):
                continue

            parent_session_stem = session_stem_for_parent(path.parent)
            info = canonicalize_transcript_name(
                ROOT,
                path.name,
                parent_session_stem=parent_session_stem,
            )
            if not info["matched"] or not info["changed"]:
                continue

            exec_target = path.with_name(info["canonical_name"])
            final_parent = Path(rewrite_path_text(str(path.parent), final_dir_map))
            final_target = final_parent / info["canonical_name"]
            plans.append(
                RenamePlan(
                    kind="file",
                    old_path=path,
                    exec_target=exec_target,
                    final_target=final_target,
                    reason=f"{path.name} -> {info['canonical_name']}",
                )
            )

    return plans


def validate_no_conflicts(plans: list[RenamePlan]) -> list[str]:
    errors: list[str] = []
    final_targets: dict[str, str] = {}
    old_paths = {str(plan.old_path) for plan in plans}

    for plan in plans:
        target_key = str(plan.final_target)
        existing = final_targets.get(target_key)
        if existing and existing != str(plan.old_path):
            errors.append(f"final collision: {existing} == {plan.old_path} -> {plan.final_target}")
        else:
            final_targets[target_key] = str(plan.old_path)

        if plan.exec_target.exists() and str(plan.exec_target) not in old_paths and plan.exec_target != plan.old_path:
            errors.append(f"existing path blocks rename: {plan.exec_target}")

    return errors


def update_transcription_log(path_map: dict[str, str]) -> str | None:
    if not LOG_PATH.exists():
        return None

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_path = STATE_DIR / f"transcription_log_backup_{timestamp}.json"
    backup_path.write_text(LOG_PATH.read_text(encoding="utf-8-sig"), encoding="utf-8")

    with open(LOG_PATH, "r", encoding="utf-8-sig") as handle:
        data = json.load(handle)

    updated: dict[str, dict] = {}
    for key, value in data.items():
        new_key = rewrite_path_text(key, path_map)
        new_value = dict(value)
        for field in ("original_path", "split_dir", "raw_path", "corrected_file", "duplicate_of"):
            field_value = new_value.get(field)
            if isinstance(field_value, str):
                new_value[field] = rewrite_path_text(field_value, path_map)

        for field in ("corrected_files", "reviewed_files", "generated_files"):
            field_value = new_value.get(field)
            if isinstance(field_value, list):
                new_value[field] = [rewrite_path_text(item, path_map) if isinstance(item, str) else item for item in field_value]

        updated[new_key] = new_value

    with open(LOG_PATH, "w", encoding="utf-8") as handle:
        json.dump(updated, handle, ensure_ascii=False, indent=2)

    return str(backup_path)


def execute_renames(file_plans: list[RenamePlan], dir_plans: list[RenamePlan]) -> None:
    for plan in sorted(file_plans, key=lambda item: len(item.old_path.parts), reverse=True):
        if plan.old_path == plan.exec_target:
            continue
        plan.old_path.rename(plan.exec_target)

    for plan in sorted(dir_plans, key=lambda item: len(item.old_path.parts), reverse=True):
        if plan.old_path == plan.exec_target:
            continue
        plan.old_path.rename(plan.exec_target)


def serialize_plan(plans: list[RenamePlan]) -> list[dict]:
    return [
        {
            "kind": plan.kind,
            "old_path": str(plan.old_path),
            "exec_target": str(plan.exec_target),
            "final_target": str(plan.final_target),
            "reason": plan.reason,
        }
        for plan in plans
    ]


def main() -> int:
    configure_stdio()

    parser = argparse.ArgumentParser(description="Rename transcript and correction files to ASCII aliases")
    parser.add_argument("--execute", action="store_true", help="Apply planned renames")
    parser.add_argument("--plan-out", help="Optional plan JSON output path")
    parser.add_argument("--log-out", help="Optional execution JSON output path")
    args = parser.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")
    plan_path = Path(args.plan_out) if args.plan_out else STATE_DIR / f"transcript_ascii_rename_plan_{today}.json"
    log_path = Path(args.log_out) if args.log_out else STATE_DIR / f"transcript_ascii_rename_log_{today}.json"

    transcript_roots = discover_transcript_roots()
    directory_rows = build_directory_plans(transcript_roots)
    dir_plans, _current_dir_map, final_dir_map = build_directory_maps(directory_rows)
    file_plans = build_file_plans(transcript_roots, final_dir_map)
    all_plans = file_plans + dir_plans
    errors = validate_no_conflicts(all_plans)

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "transcript_roots": [str(path) for path in transcript_roots],
        "file_count": len(file_plans),
        "dir_count": len(dir_plans),
        "errors": errors,
        "entries": serialize_plan(all_plans),
    }
    plan_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PLAN={plan_path}")
    print(f"FILES={len(file_plans)}")
    print(f"DIRS={len(dir_plans)}")
    print(f"ERRORS={len(errors)}")

    if errors or not args.execute:
        return 1 if errors else 0

    execute_renames(file_plans, dir_plans)

    final_path_map = {str(plan.old_path): str(plan.final_target) for plan in all_plans}
    backup_path = update_transcription_log(final_path_map)

    log_payload = {
        "executed_at": datetime.now().isoformat(timespec="seconds"),
        "file_count": len(file_plans),
        "dir_count": len(dir_plans),
        "transcription_log_backup": backup_path,
        "entries": serialize_plan(all_plans),
    }
    log_path.write_text(json.dumps(log_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"LOG={log_path}")
    if backup_path:
        print(f"TRANSCRIPTION_LOG_BACKUP={backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
