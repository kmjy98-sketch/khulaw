#!/usr/bin/env python3
"""
Helpers for transcript duplicate detection.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from correction_state import list_corrected_files, list_raw_parts, normalize_existing_lists


def is_inbox_path(path: str) -> bool:
    normalized = path.replace("/", "\\").lower()
    return "\\_inbox\\" in normalized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def candidate_metrics(transcript_path: str, info: dict) -> dict:
    split_dir = Path(info.get("split_dir") or "")
    generated_files, reviewed_files = normalize_existing_lists(info, split_dir)
    raw_parts = list_raw_parts(split_dir)
    corrected_files = list_corrected_files(split_dir)
    return {
        "in_inbox": is_inbox_path(transcript_path),
        "reviewed_count": len(reviewed_files),
        "generated_count": len(generated_files),
        "part_count": len(raw_parts),
        "corrected_count": len(corrected_files),
    }


def canonical_score(transcript_path: str, info: dict) -> tuple:
    metrics = candidate_metrics(transcript_path, info)
    return (
        0 if metrics["in_inbox"] else 1,
        1 if metrics["reviewed_count"] else 0,
        metrics["reviewed_count"],
        1 if metrics["part_count"] else 0,
        metrics["part_count"],
        1 if metrics["corrected_count"] else 0,
        metrics["corrected_count"],
        1 if metrics["generated_count"] else 0,
        metrics["generated_count"],
        -len(transcript_path),
        transcript_path,
    )


def duplicate_reason(
    transcript_path: str,
    info: dict,
    canonical_path: str,
    canonical_info: dict,
) -> str:
    metrics = candidate_metrics(transcript_path, info)
    canonical_metrics = candidate_metrics(canonical_path, canonical_info)
    reasons: list[str] = ["same SHA256"]

    if metrics["in_inbox"] and not canonical_metrics["in_inbox"]:
        reasons.append("prefer non-_inbox path")
    elif canonical_metrics["reviewed_count"] > metrics["reviewed_count"]:
        reasons.append("canonical path has reviewed correction files")
    elif canonical_metrics["part_count"] > metrics["part_count"]:
        reasons.append("canonical path has split part files")
    else:
        reasons.append("prefer canonical transcript path")

    return "; ".join(reasons)


def build_duplicate_index(log_data: dict) -> dict[str, dict]:
    groups: dict[str, list[tuple[str, dict]]] = {}

    for transcript_path, info in log_data.items():
        path = Path(transcript_path)
        if not path.exists() or not path.is_file():
            continue
        digest = sha256_file(path)
        groups.setdefault(digest, []).append((transcript_path, info))

    duplicates: dict[str, dict] = {}
    for digest, rows in groups.items():
        if len(rows) < 2:
            continue

        canonical_path, canonical_info = max(rows, key=lambda row: canonical_score(row[0], row[1]))
        for transcript_path, info in rows:
            if transcript_path == canonical_path:
                continue
            if not is_inbox_path(transcript_path):
                continue
            duplicates[transcript_path] = {
                "duplicate_of": canonical_path,
                "duplicate_reason": duplicate_reason(transcript_path, info, canonical_path, canonical_info),
                "duplicate_sha256": digest,
            }

    return duplicates
