#!/usr/bin/env python3
"""
Backfill correction state fields across the full transcription log.
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from correction_state import derive_state, normalize_existing_lists
from duplicate_transcripts import build_duplicate_index

ROOT = Path(__file__).resolve().parents[4]
LOG_PATH = ROOT / ".agent" / "state" / "transcription_log.json"


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


def sync_entry(transcript_path: str, info: dict, duplicate_index: dict[str, dict]) -> str:
    split_dir = Path(info.get("split_dir") or "")
    duplicate_info = duplicate_index.get(transcript_path)
    info["duplicate_of"] = duplicate_info["duplicate_of"] if duplicate_info else ""
    info["duplicate_reason"] = duplicate_info["duplicate_reason"] if duplicate_info else ""
    generated_files, reviewed_files = normalize_existing_lists(info, split_dir)
    state_info = derive_state(
        info,
        split_dir,
        generated_files=generated_files,
        reviewed_files=reviewed_files,
        stale_reason=info.get("stale_reason") or None,
    )

    info["corrected"] = state_info["corrected"]
    info["correction_state"] = state_info["correction_state"]
    info["corrected_files"] = reviewed_files
    info["reviewed_files"] = reviewed_files
    info["generated_files"] = generated_files
    info["corrected_file"] = reviewed_files[-1] if reviewed_files else None
    info["part_count"] = state_info["part_count"]
    info["expected_total"] = state_info["expected_total"]
    info["stale_reason"] = state_info["stale_reason"]
    info["duplicate_of"] = state_info["duplicate_of"]
    info["duplicate_reason"] = state_info["duplicate_reason"]
    info["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return state_info["correction_state"]


def main() -> int:
    configure_stdio()

    parser = argparse.ArgumentParser(description="Backfill correction_state fields across the transcription log")
    parser.add_argument("--dry-run", action="store_true", help="Preview updates without writing the log")
    args = parser.parse_args()

    data = load_log()
    duplicate_index = build_duplicate_index(data)
    counts = Counter()

    for transcript_path, info in data.items():
        counts[sync_entry(transcript_path, info, duplicate_index)] += 1

    print("STATE_COUNTS=" + json.dumps(dict(sorted(counts.items())), ensure_ascii=False))
    print(f"TOTAL={len(data)}")

    if args.dry_run:
        print("DRY_RUN=1")
        return 0

    save_log(data)
    print(f"UPDATED_LOG={LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
