#!/usr/bin/env python3
"""
Batch-run mark_corrected.py for pending transcript correction entries.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from correction_state import derive_state, list_corrected_files
from duplicate_transcripts import build_duplicate_index

ROOT = Path(__file__).resolve().parents[4]
LOG_PATH = ROOT / ".agent" / "state" / "transcription_log.json"
MARK_SCRIPT = Path(__file__).resolve().parent / "mark_corrected.py"


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_log() -> dict:
    with open(LOG_PATH, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def pick_corrected_file(split_dir: Path) -> Path | None:
    candidates = list_corrected_files(split_dir)
    if candidates:
        return candidates[0]
    return None


def collect_targets(include_duplicates: bool) -> list[dict]:
    data = load_log()
    duplicate_index = build_duplicate_index(data)
    rows = []
    seen = set()

    for transcript_path, info in data.items():
        split_dir = Path(info.get("split_dir") or "")
        effective_info = dict(info)
        duplicate_info = duplicate_index.get(transcript_path)
        effective_info["duplicate_of"] = duplicate_info["duplicate_of"] if duplicate_info else ""
        effective_info["duplicate_reason"] = duplicate_info["duplicate_reason"] if duplicate_info else ""
        state_info = derive_state(effective_info, split_dir)
        if state_info["correction_state"] in {"reviewed", "duplicate"}:
            continue
        key = transcript_path if include_duplicates else str(split_dir) or transcript_path
        if key in seen:
            continue
        seen.add(key)

        corrected_file = pick_corrected_file(split_dir) if split_dir.exists() else None
        rows.append(
            {
                "transcript_path": transcript_path,
                "split_dir": str(split_dir),
                "correction_state": state_info["correction_state"],
                "expected_total": state_info["expected_total"],
                "corrected_count": state_info["corrected_count"],
                "stale_reason": state_info["stale_reason"],
                "corrected_file": str(corrected_file) if corrected_file else None,
            }
        )

    rows.sort(key=lambda row: row["transcript_path"])
    return rows


def resolve_mode(row_state: str, requested_mode: str) -> str:
    if requested_mode != "auto":
        return requested_mode
    if row_state == "generated":
        return "generated"
    return "reviewed"


def run_mark(
    corrected_file: str,
    dry_run: bool,
    note: str | None,
    skip_progress: bool,
    skip_index: bool,
    mode: str,
    sync_dir: bool,
) -> int:
    command = [sys.executable, str(MARK_SCRIPT), corrected_file]
    if dry_run:
        command.append("--dry-run")
    if note:
        command.extend(["--note", note])
    command.extend(["--mode", mode])
    if sync_dir:
        command.append("--sync-dir")
    if skip_progress:
        command.append("--skip-progress")
    if skip_index:
        command.append("--skip-index")
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    return result.returncode


def main() -> int:
    configure_stdio()

    parser = argparse.ArgumentParser(description="Batch-run mark_corrected.py for pending transcript correction entries.")
    parser.add_argument("--include-duplicates", action="store_true", help="Keep duplicate log rows instead of collapsing by split_dir")
    parser.add_argument("--dry-run", action="store_true", help="Call mark_corrected.py with --dry-run")
    parser.add_argument("--note", help="Optional note passed through to mark_corrected.py")
    parser.add_argument("--mode", choices=("auto", "reviewed", "generated"), default="auto", help="Correction mode to apply")
    parser.add_argument("--no-sync-dir", action="store_true", help="Disable syncing every corrected file found in the folder")
    parser.add_argument("--skip-progress", action="store_true", help="Skip progress.py hooks")
    parser.add_argument("--skip-index", action="store_true", help="Skip update_index.py hooks")
    args = parser.parse_args()

    rows = collect_targets(include_duplicates=args.include_duplicates)
    runnable = [row for row in rows if row["corrected_file"]]
    blocked = [row for row in rows if not row["corrected_file"]]

    print(f"TOTAL_PENDING={len(rows)}")
    print(f"RUNNABLE={len(runnable)}")
    print(f"BLOCKED={len(blocked)}")

    for row in blocked:
        print("---")
        print(f"BLOCKED transcript_path: {row['transcript_path']}")
        print(f"BLOCKED split_dir: {row['split_dir']}")
        print(f"BLOCKED state: {row['correction_state']}")
        if row["stale_reason"]:
            print(f"BLOCKED reason: {row['stale_reason']}")
        else:
            print("BLOCKED reason: corrected file not found")

    for row in runnable:
        print("---")
        print(f"RUN transcript_path: {row['transcript_path']}")
        print(f"RUN corrected_file: {row['corrected_file']}")
        print(f"RUN state: {row['correction_state']}")
        print(f"RUN corrected_count: {row['corrected_count']} / {row['expected_total']}")
        effective_mode = resolve_mode(row["correction_state"], args.mode)
        print(f"RUN mode: {effective_mode}")
        code = run_mark(
            row["corrected_file"],
            dry_run=args.dry_run,
            note=args.note,
            skip_progress=args.skip_progress,
            skip_index=args.skip_index,
            mode=effective_mode,
            sync_dir=not args.no_sync_dir,
        )
        if code != 0:
            print(f"RUN result: failed ({code})")
        else:
            print("RUN result: ok")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
