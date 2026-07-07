#!/usr/bin/env python3
"""
Repair stale transcription log paths when a simple alias replacement matches a real path.
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LOG_PATH = ROOT / ".agent" / "state" / "transcription_log.json"

DEFAULT_REPLACEMENTS = [
    ("\\5.??\\", "\\5.기타\\"),
]


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_log() -> dict:
    with open(LOG_PATH, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def save_log(data: dict) -> None:
    with open(LOG_PATH, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def repair_path(path: str | None, replacements: list[tuple[str, str]]) -> str | None:
    if not path:
        return path
    if os.path.exists(path):
        return path
    for old, new in replacements:
        if old not in path:
            continue
        candidate = path.replace(old, new)
        if os.path.exists(candidate):
            return candidate
    return path


def repair_value(value, replacements: list[tuple[str, str]]):
    if isinstance(value, str):
        return repair_path(value, replacements)
    if isinstance(value, list):
        return [repair_value(item, replacements) for item in value]
    return value


def parse_replacements(raw_items: list[str]) -> list[tuple[str, str]]:
    replacements = []
    for item in raw_items:
        old, sep, new = item.partition("=")
        if not sep:
            raise ValueError(f"invalid replacement: {item}")
        replacements.append((old, new))
    return replacements


def main() -> int:
    configure_stdio()

    parser = argparse.ArgumentParser(description="Repair stale transcript log paths by alias replacement")
    parser.add_argument("--dry-run", action="store_true", help="Preview replacements without writing the log")
    parser.add_argument(
        "--replace",
        action="append",
        default=[],
        help="Alias replacement in the form old=new; may be supplied multiple times",
    )
    args = parser.parse_args()

    replacements = DEFAULT_REPLACEMENTS + parse_replacements(args.replace)
    data = load_log()

    repaired = {}
    resolved = []
    unresolved = []
    conflicts = []

    for key, info in data.items():
        if info.get("correction_state") != "stale":
            repaired[key] = info
            continue

        new_key = repair_path(key, replacements)
        new_info = dict(info)
        for field in (
            "split_dir",
            "original_path",
            "raw_path",
            "corrected_file",
            "corrected_files",
            "reviewed_files",
            "generated_files",
            "duplicate_of",
        ):
            if field in new_info:
                new_info[field] = repair_value(new_info[field], replacements)

        if new_key == key:
            unresolved.append(key)
            repaired[key] = info
            continue

        if new_key in repaired or new_key in data:
            conflicts.append((key, new_key))
            repaired[key] = info
            continue

        resolved.append((key, new_key))
        repaired[new_key] = new_info

    print(f"RESOLVED={len(resolved)}")
    for old_key, new_key in resolved:
        print("---")
        print(f"old: {old_key}")
        print(f"new: {new_key}")

    print(f"UNRESOLVED={len(unresolved)}")
    for key in unresolved:
        print(f"unresolved: {key}")

    print(f"CONFLICTS={len(conflicts)}")
    for old_key, new_key in conflicts:
        print("---")
        print(f"conflict_old: {old_key}")
        print(f"conflict_new: {new_key}")

    if args.dry_run:
        print("DRY_RUN=1")
        return 0

    save_log(repaired)
    print(f"UPDATED_LOG={LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
