#!/usr/bin/env python3
"""
List uncorrected transcripts from transcription_log.json.
"""

import argparse
import json
import sys
from pathlib import Path

from correction_state import derive_state, list_corrected_files, list_raw_parts
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


def summarize(include_duplicates: bool) -> dict:
    data = load_log()
    duplicate_index = build_duplicate_index(data)
    pending = []
    stale = []
    duplicates = []
    counts = {
        "uncorrected": 0,
        "generated": 0,
        "partial_reviewed": 0,
        "stale": 0,
        "duplicate": 0,
    }
    seen = set()

    for transcript_path, info in data.items():
        split_dir = Path(info.get("split_dir") or "")
        effective_info = dict(info)
        duplicate_info = duplicate_index.get(transcript_path)
        effective_info["duplicate_of"] = duplicate_info["duplicate_of"] if duplicate_info else ""
        effective_info["duplicate_reason"] = duplicate_info["duplicate_reason"] if duplicate_info else ""
        state_info = derive_state(effective_info, split_dir)
        if state_info["correction_state"] == "reviewed":
            continue
        key = transcript_path if include_duplicates else str(split_dir) or transcript_path
        if key in seen:
            continue
        seen.add(key)

        part_files = list_raw_parts(split_dir)
        corrected_files = list_corrected_files(split_dir)
        row = {
            "transcript_path": transcript_path,
            "split_dir": str(split_dir),
            "correction_state": state_info["correction_state"],
            "duplicate_of": state_info["duplicate_of"],
            "duplicate_reason": state_info["duplicate_reason"],
            "part_count": len(part_files),
            "corrected_count": len(corrected_files),
            "reviewed_count": len(state_info["reviewed_files"]),
            "generated_count": len(state_info["generated_files"]),
            "expected_total": state_info["expected_total"],
            "stale_reason": state_info["stale_reason"],
            "sample_parts": [path.name for path in part_files[:3]],
            "sample_corrected": [path.name for path in corrected_files[:3]],
        }
        counts[state_info["correction_state"]] += 1

        if state_info["correction_state"] == "stale":
            stale.append(row)
        elif state_info["correction_state"] == "duplicate":
            duplicates.append(row)
        else:
            pending.append(row)

    pending.sort(key=lambda row: row["transcript_path"])
    stale.sort(key=lambda row: row["transcript_path"])
    duplicates.sort(key=lambda row: row["transcript_path"])
    return {
        "pending": pending,
        "stale": stale,
        "duplicates": duplicates,
        "counts": counts,
    }


def print_rows(payload: dict) -> None:
    pending = payload["pending"]
    stale = payload["stale"]
    duplicates = payload["duplicates"]
    counts = payload["counts"]

    print(f"REVIEW_PENDING_COUNT={len(pending)}")
    print(f"UNCORRECTED_COUNT={counts['uncorrected']}")
    print(f"GENERATED_COUNT={counts['generated']}")
    print(f"PARTIAL_REVIEWED_COUNT={counts['partial_reviewed']}")
    print(f"STALE_COUNT={len(stale)}")
    print(f"DUPLICATE_COUNT={len(duplicates)}")
    for row in pending:
        print("---")
        print(f"transcript_path: {row['transcript_path']}")
        print(f"split_dir: {row['split_dir']}")
        print(f"correction_state: {row['correction_state']}")
        print(f"part_count: {row['part_count']}")
        print(f"corrected_count: {row['corrected_count']}")
        print(f"reviewed_count: {row['reviewed_count']}")
        print(f"generated_count: {row['generated_count']}")
        print(f"expected_total: {row['expected_total']}")
        print(f"sample_parts: {', '.join(row['sample_parts'])}")
        print(f"sample_corrected: {', '.join(row['sample_corrected'])}")
    for row in stale:
        print("---")
        print(f"stale_transcript_path: {row['transcript_path']}")
        print(f"stale_split_dir: {row['split_dir']}")
        print(f"stale_reason: {row['stale_reason']}")
    for row in duplicates:
        print("---")
        print(f"duplicate_transcript_path: {row['transcript_path']}")
        print(f"duplicate_split_dir: {row['split_dir']}")
        print(f"duplicate_of: {row['duplicate_of']}")
        print(f"duplicate_reason: {row['duplicate_reason']}")


def main() -> int:
    configure_stdio()

    parser = argparse.ArgumentParser(description="미교정 전사문 목록 출력")
    parser.add_argument("--include-duplicates", action="store_true", help="로그 중복 경로도 그대로 포함")
    parser.add_argument("--json", action="store_true", help="JSON으로 출력")
    parser.add_argument("--output", help="결과 저장 파일 경로")
    args = parser.parse_args()

    payload_obj = summarize(include_duplicates=args.include_duplicates)

    if args.json:
        payload = json.dumps(payload_obj, ensure_ascii=False, indent=2)
    else:
        from io import StringIO

        buffer = StringIO()
        stdout = sys.stdout
        sys.stdout = buffer
        try:
            print_rows(payload_obj)
        finally:
            sys.stdout = stdout
        payload = buffer.getvalue()
        print(payload, end="")

    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
        print(f"SAVED={target}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
