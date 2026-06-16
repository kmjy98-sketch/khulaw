#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


PROBLEM_KINDS = ("dt", "case", "textbook")


def find_workspace_root() -> Path | None:
    candidates = [Path.cwd().resolve(), Path(__file__).resolve()]
    seen: set[Path] = set()
    for candidate in candidates:
        for parent in [candidate, *candidate.parents]:
            if parent in seen:
                continue
            seen.add(parent)
            if (parent / ".agent").exists():
                return parent
    return None


def workspace_root_or_raise() -> Path:
    workspace_root = find_workspace_root()
    if workspace_root is None:
        raise FileNotFoundError("workspace root with .agent was not found")
    return workspace_root


def problem_index_path(workspace_root: Path) -> Path:
    return workspace_root / ".agent" / "state" / "problem_index.json"


def unresolved_manifest_path(workspace_root: Path) -> Path:
    return workspace_root / ".agent" / "state" / "problem_index_unresolved.json"


def rename_log_path(workspace_root: Path) -> Path:
    return workspace_root / ".agent" / "state" / "rename_violations_log.json"


def workspace_relative(path: Path, workspace_root: Path) -> str:
    return str(path.resolve().relative_to(workspace_root.resolve())).replace("/", "\\")


def extract_number(text: Any, token: str) -> int | None:
    if not isinstance(text, str):
        return None
    index = text.find(token)
    if index < 0:
        return None
    index += len(token)
    while index < len(text) and not text[index].isdigit():
        index += 1
    digits: list[str] = []
    while index < len(text) and text[index].isdigit():
        digits.append(text[index])
        index += 1
    return int("".join(digits)) if digits else None


def pick_unique(candidates: list[Path]) -> Path | None:
    return candidates[0] if len(candidates) == 1 else None


def find_song_dt(workspace_root: Path, lecture: int, keyword: str) -> Path | None:
    base_dir = workspace_root / "1.민사" / "송영곤_기본민법" / "강의자료" / "선택형"
    candidates = [
        path
        for path in base_dir.glob("*.pdf")
        if "민법_송영곤_DT_" in path.name and f"_{lecture}회" in path.name and keyword in path.name
    ]
    return pick_unique(candidates)


def find_yoon_dt(workspace_root: Path, lecture: int, keyword: str) -> Path | None:
    base_dir = workspace_root / "1.민사" / "보관" / "윤동환_민법의맥" / "강의자료" / "선택형"
    candidates = [
        path
        for path in base_dir.glob("*.pdf")
        if f"DT{lecture}회" in path.name and keyword in path.name
    ]
    return pick_unique(candidates)


def find_yoon_case(workspace_root: Path, lecture: int, keyword: str) -> Path | None:
    base_dir = workspace_root / "1.민사" / "보관" / "윤동환_민법의맥" / "강의자료" / "모의답안"
    prefix = f"3-{lecture + 1}_"
    candidates = [
        path
        for path in base_dir.glob("*.pdf")
        if prefix in path.name and f"모의{lecture}회" in path.name and "윤동환" in path.name and keyword in path.name
    ]
    return pick_unique(candidates)


def find_reference_material(workspace_root: Path, file_ref: str) -> Path | None:
    base_dir = workspace_root / "1.민사" / "기타자료"
    legacy_name = Path(file_ref).name
    markers = ["13회", "47등"]
    suffix = None
    for marker in markers:
        index = legacy_name.find(marker)
        if index >= 0:
            suffix = legacy_name[index:]
            break
    if suffix is None:
        return None
    candidates = [path for path in base_dir.glob("*.pdf") if suffix in path.name]
    return pick_unique(candidates)


def load_rename_targets(workspace_root: Path) -> dict[str, str]:
    log_path = rename_log_path(workspace_root)
    if not log_path.exists():
        return {}

    with open(log_path, "r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)

    details = payload.get("details", []) if isinstance(payload, dict) else []
    targets: dict[str, str] = {}
    for detail in details:
        if not isinstance(detail, dict):
            continue
        if detail.get("status") != "OK" or detail.get("type") != "file_rename":
            continue
        old_ref = detail.get("old")
        new_ref = detail.get("new")
        if not isinstance(old_ref, str) or not isinstance(new_ref, str):
            continue
        targets[Path(old_ref).name.casefold()] = Path(new_ref).name
    return targets


def resolve_legacy_paths(item: dict[str, Any], workspace_root: Path) -> tuple[Path | None, Path | None]:
    file_ref = item.get("file")
    answer_ref = item.get("answer_source")

    if not isinstance(file_ref, str):
        return None, None

    lowered_file = file_ref.casefold()
    lowered_answer = answer_ref.casefold() if isinstance(answer_ref, str) else ""

    if "송영곤 dt" in lowered_file or "송영곤_dt" in lowered_file:
        lecture = extract_number(file_ref, "DT") or extract_number(answer_ref, "DT")
        if lecture is None:
            return None, None
        return find_song_dt(workspace_root, lecture, "문제"), find_song_dt(workspace_root, lecture, "해설")

    if "윤동환 dt" in lowered_file or "윤동환_dt" in lowered_file:
        lecture = extract_number(file_ref, "DT") or extract_number(answer_ref, "DT")
        if lecture is None:
            return None, None
        return find_yoon_dt(workspace_root, lecture, "문제"), find_yoon_dt(workspace_root, lecture, "해설")

    if ("윤동환" in file_ref or file_ref.startswith("보관\\3-")) and "모의" in f"{file_ref}{answer_ref or ''}":
        lecture = extract_number(file_ref, "모의") or extract_number(answer_ref, "모의")
        if lecture is None:
            return None, None
        file_keyword = "채점" if "채점" in file_ref else "문제"
        answer_keyword = "채점" if "채점" in lowered_answer else "해설"
        return find_yoon_case(workspace_root, lecture, file_keyword), find_yoon_case(workspace_root, lecture, answer_keyword)

    if file_ref.startswith("참고자료\\"):
        reference_file = find_reference_material(workspace_root, file_ref)
        if reference_file is not None:
            return reference_file, reference_file

    return None, None


def suggest_legacy_dt_candidate(
    item: dict[str, Any],
    workspace_root: Path,
    rename_targets: dict[str, str],
) -> dict[str, Any] | None:
    file_ref = item.get("file")
    if not isinstance(file_ref, str):
        return None

    legacy_name = Path(file_ref).name
    if "DT" not in legacy_name or "문제" not in legacy_name:
        return None

    lookup_keys = [legacy_name.casefold()]
    if legacy_name.startswith("(") and ")DT" in legacy_name:
        lookup_keys.append(legacy_name[1:].replace(")DT", "_DT", 1).casefold())
    logged_target = next((rename_targets[key] for key in lookup_keys if key in rename_targets), None)
    if logged_target is None:
        return None

    lecture = extract_number(legacy_name, "DT") or extract_number(logged_target, "DT")
    if lecture is None:
        return None

    candidate_file = find_song_dt(workspace_root, lecture, "문제")
    candidate_answer = find_song_dt(workspace_root, lecture, "해설")
    if candidate_file is None and candidate_answer is None:
        return None

    suggestion: dict[str, Any] = {
        "candidate_kind": "dt",
        "requires_manual_reclassification": True,
        "candidate_reason": "rename_violations_log match",
        "rename_log_target": logged_target,
    }
    if candidate_file is not None:
        suggestion["candidate_file"] = workspace_relative(candidate_file, workspace_root)
    if candidate_answer is not None:
        suggestion["candidate_answer_source"] = workspace_relative(candidate_answer, workspace_root)
    return suggestion


def normalize_item(item: Any, workspace_root: Path, stats: dict[str, int]) -> Any:
    if not isinstance(item, dict):
        return item

    normalized = dict(item)
    if normalized.get("answer") is None and normalized.get("verified") is True:
        normalized["verified"] = False
        stats["verified_downgraded"] += 1
    if normalized.get("answer") is None and normalized.get("last_verified") is not None:
        normalized["last_verified"] = None
        stats["last_verified_cleared"] += 1

    source_path = normalized.get("source_path")
    if isinstance(source_path, str) and source_path:
        source_file = Path(source_path)
        if source_file.exists():
            actual_ref = workspace_relative(source_file, workspace_root)
            if normalized.get("file") != actual_ref:
                if normalized.get("file") and not normalized.get("display_label"):
                    normalized["display_label"] = normalized["file"]
                normalized["file"] = actual_ref
                stats["file_rewritten_from_source_path"] += 1
            resolved_source = str(source_file.resolve())
            if normalized.get("source_path") != resolved_source:
                normalized["source_path"] = resolved_source
                stats["source_path_normalized"] += 1

    file_path = Path(normalized["file"]) if isinstance(normalized.get("file"), str) else None
    if file_path is not None and not file_path.is_absolute() and not (workspace_root / file_path).exists():
        legacy_file, legacy_answer = resolve_legacy_paths(normalized, workspace_root)
        if legacy_file is not None:
            legacy_ref = workspace_relative(legacy_file, workspace_root)
            if normalized.get("file") != legacy_ref:
                if normalized.get("file") and not normalized.get("display_label"):
                    normalized["display_label"] = normalized["file"]
                normalized["file"] = legacy_ref
                normalized["source_path"] = str(legacy_file.resolve())
                stats["legacy_file_resolved"] += 1
        if legacy_answer is not None:
            legacy_answer_ref = workspace_relative(legacy_answer, workspace_root)
            if normalized.get("answer_source") != legacy_answer_ref:
                normalized["answer_source"] = legacy_answer_ref
                stats["legacy_answer_resolved"] += 1

    return normalized


def repair_index(index: dict[str, Any], workspace_root: Path) -> dict[str, int]:
    stats = {
        "items_seen": 0,
        "verified_downgraded": 0,
        "last_verified_cleared": 0,
        "file_rewritten_from_source_path": 0,
        "source_path_normalized": 0,
        "legacy_file_resolved": 0,
        "legacy_answer_resolved": 0,
    }

    for subject_data in index.get("subjects", {}).values():
        for topic_data in subject_data.get("topics", {}).values():
            problems = topic_data.get("problems", {})
            if not isinstance(problems, dict):
                continue
            for problem_kind in PROBLEM_KINDS:
                items = problems.get(problem_kind, [])
                repaired: list[Any] = []
                for item in items:
                    stats["items_seen"] += 1
                    repaired.append(normalize_item(item, workspace_root, stats))
                problems[problem_kind] = repaired

    return stats


def prune_candidate_case_overlaps(
    index: dict[str, Any],
    unresolved: list[dict[str, Any]],
) -> dict[str, int]:
    stats = {
        "candidate_overlap_removed": 0,
        "candidate_overlap_skipped": 0,
    }

    for entry in unresolved:
        if entry.get("kind") != "case" or entry.get("candidate_kind") != "dt":
            continue

        subject_name = entry.get("subject")
        topic_name = entry.get("topic")
        candidate_file = entry.get("candidate_file")
        legacy_file = entry.get("file")
        legacy_answer = entry.get("answer_source")
        if not all(isinstance(value, str) and value for value in (subject_name, topic_name, candidate_file, legacy_file)):
            stats["candidate_overlap_skipped"] += 1
            continue

        subject_data = index.get("subjects", {}).get(subject_name)
        if not isinstance(subject_data, dict):
            stats["candidate_overlap_skipped"] += 1
            continue
        topic_data = subject_data.get("topics", {}).get(topic_name)
        if not isinstance(topic_data, dict):
            stats["candidate_overlap_skipped"] += 1
            continue
        problems = topic_data.get("problems", {})
        if not isinstance(problems, dict):
            stats["candidate_overlap_skipped"] += 1
            continue

        dt_items = problems.get("dt", [])
        if not any(isinstance(item, dict) and item.get("file") == candidate_file for item in dt_items):
            stats["candidate_overlap_skipped"] += 1
            continue

        case_items = problems.get("case", [])
        updated_case_items: list[Any] = []
        removed_here = 0
        for item in case_items:
            if not isinstance(item, dict):
                updated_case_items.append(item)
                continue
            if item.get("file") == legacy_file and item.get("answer_source") == legacy_answer:
                removed_here += 1
                continue
            updated_case_items.append(item)

        if removed_here == 0:
            stats["candidate_overlap_skipped"] += 1
            continue

        problems["case"] = updated_case_items
        stats["candidate_overlap_removed"] += removed_here

    return stats


def collect_unresolved(index: dict[str, Any], workspace_root: Path) -> list[dict[str, Any]]:
    unresolved: list[dict[str, Any]] = []
    rename_targets = load_rename_targets(workspace_root)
    for subject_name, subject_data in index.get("subjects", {}).items():
        for topic_name, topic_data in subject_data.get("topics", {}).items():
            problems = topic_data.get("problems", {})
            if not isinstance(problems, dict):
                continue
            for problem_kind in PROBLEM_KINDS:
                for item in problems.get(problem_kind, []):
                    if not isinstance(item, dict):
                        continue
                    file_ref = item.get("file")
                    if isinstance(file_ref, str) and file_ref and not (workspace_root / file_ref).exists():
                        entry = {
                            "subject": subject_name,
                            "topic": topic_name,
                            "kind": problem_kind,
                            "file": file_ref,
                            "answer_source": item.get("answer_source"),
                        }
                        suggestion = suggest_legacy_dt_candidate(item, workspace_root, rename_targets)
                        if suggestion is not None:
                            entry.update(suggestion)
                        unresolved.append(entry)
    return unresolved


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair and reconcile problem_index.json")
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing files")
    parser.add_argument(
        "--prune-candidate-overlaps",
        action="store_true",
        help="remove legacy case entries when the same topic already has the matching dt file",
    )
    args = parser.parse_args()

    workspace_root = workspace_root_or_raise()
    index_path = problem_index_path(workspace_root)
    with open(index_path, "r", encoding="utf-8-sig") as handle:
        index = json.load(handle)

    stats = repair_index(index, workspace_root)
    unresolved = collect_unresolved(index, workspace_root)
    if args.prune_candidate_overlaps:
        stats.update(prune_candidate_case_overlaps(index, unresolved))
        unresolved = collect_unresolved(index, workspace_root)
    stats["unresolved_count"] = len(unresolved)
    stats["unresolved_with_candidate"] = sum(1 for entry in unresolved if "candidate_file" in entry)
    if not args.dry_run:
        index["version"] = "2.0"
        index["last_updated"] = str(date.today())
        with open(index_path, "w", encoding="utf-8") as handle:
            json.dump(index, handle, ensure_ascii=False, indent=2)
        manifest_path = unresolved_manifest_path(workspace_root)
        manifest = {
            "generated_at": str(date.today()),
            "count": len(unresolved),
            "entries": unresolved,
        }
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)

    print(json.dumps({"dry_run": args.dry_run, **stats}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
