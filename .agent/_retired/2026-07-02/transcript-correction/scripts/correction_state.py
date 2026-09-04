#!/usr/bin/env python3
"""
Shared correction-state helpers.
"""

from __future__ import annotations

from pathlib import Path

COR_SUFFIX = "_corr.md"
LEGACY_COR_SUFFIXES = ("_\uad50\uc815.md", "_corrected.md")
ALL_CORRECTED_SUFFIXES = (COR_SUFFIX, *LEGACY_COR_SUFFIXES)
GENERATED_NOTE_TOKEN = "generated heuristic corrected files"


def is_corrected_name(name: str) -> bool:
    return any((name or "").endswith(suffix) for suffix in ALL_CORRECTED_SUFFIXES)


def unique_strings(values: list[str] | tuple[str, ...] | None) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values or []:
        if not value:
            continue
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        rows.append(text)
    return rows


def list_raw_parts(split_dir: Path) -> list[Path]:
    if not split_dir.exists():
        return []
    return sorted(path for path in split_dir.glob("*_part*.md") if not is_corrected_name(path.name))


def list_corrected_files(split_dir: Path) -> list[Path]:
    if not split_dir.exists():
        return []
    return sorted(path for path in split_dir.iterdir() if path.is_file() and is_corrected_name(path.name))


def normalize_existing_lists(info: dict, split_dir: Path) -> tuple[list[str], list[str]]:
    generated_files = unique_strings(info.get("generated_files") or [])
    reviewed_files = unique_strings(info.get("reviewed_files") or [])

    legacy_files = unique_strings(info.get("corrected_files") or [])
    legacy_single = info.get("corrected_file")
    if legacy_single:
        legacy_files = unique_strings([*legacy_files, legacy_single])

    state = info.get("correction_state") or ""
    notes = info.get("notes", "") or ""
    all_corrected = [str(path) for path in list_corrected_files(split_dir)]

    if state == "generated" or GENERATED_NOTE_TOKEN in notes:
        generated_files = unique_strings([*generated_files, *legacy_files, *all_corrected])
    elif state in {"reviewed", "partial_reviewed"} or info.get("corrected"):
        reviewed_files = unique_strings([*reviewed_files, *legacy_files, *all_corrected])
    else:
        reviewed_files = unique_strings([*reviewed_files, *legacy_files])

    return generated_files, reviewed_files


def merge_mode_files(
    info: dict,
    split_dir: Path,
    mode: str,
    paths: list[str],
) -> tuple[list[str], list[str]]:
    generated_files, reviewed_files = normalize_existing_lists(info, split_dir)
    merged_paths = unique_strings(paths)

    if mode == "generated":
        generated_files = unique_strings([*generated_files, *merged_paths])
    else:
        reviewed_files = unique_strings([*reviewed_files, *merged_paths])
        generated_files = [path for path in generated_files if path not in merged_paths]

    return generated_files, reviewed_files


def derive_state(
    info: dict,
    split_dir: Path,
    generated_files: list[str] | None = None,
    reviewed_files: list[str] | None = None,
    stale_reason: str | None = None,
) -> dict:
    raw_parts = list_raw_parts(split_dir)
    corrected_paths = list_corrected_files(split_dir)
    duplicate_of = info.get("duplicate_of") or ""
    duplicate_reason = info.get("duplicate_reason") or ""

    if generated_files is None or reviewed_files is None:
        generated_files, reviewed_files = normalize_existing_lists(info, split_dir)
    else:
        generated_files = unique_strings(generated_files)
        reviewed_files = unique_strings(reviewed_files)

    if duplicate_of:
        state = "duplicate"
        corrected = False
        expected_total = len(raw_parts) if raw_parts else (1 if corrected_paths else 0)
    elif not split_dir.exists():
        state = "stale"
        corrected = False
        expected_total = 0
        stale_reason = stale_reason or "split_dir missing"
    else:
        expected_total = len(raw_parts) if raw_parts else (1 if corrected_paths else 0)
        reviewed_count = len(reviewed_files)
        generated_count = len(generated_files)
        if expected_total and reviewed_count >= expected_total:
            state = "reviewed"
            corrected = True
        elif reviewed_count > 0:
            state = "partial_reviewed"
            corrected = False
        elif generated_count > 0:
            state = "generated"
            corrected = False
        else:
            state = "uncorrected"
            corrected = False

    return {
        "correction_state": state,
        "corrected": corrected,
        "generated_files": generated_files,
        "reviewed_files": reviewed_files,
        "part_count": len(raw_parts),
        "expected_total": expected_total,
        "corrected_count": len(corrected_paths),
        "stale_reason": stale_reason if state == "stale" else "",
        "duplicate_of": duplicate_of,
        "duplicate_reason": duplicate_reason,
    }
