#!/usr/bin/env python3
"""Build a canonical PDF manifest from the current workspace files."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / ".agent" / "state"
PROBLEM_INDEX_PATH = STATE_DIR / "problem_index.json"
CHUNKS_INDEX_PATH = ROOT / ".agent" / "data" / "pdf_extracts" / "chunks_index.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_filename(name: str) -> str:
    value = unicodedata.normalize("NFKC", Path(name).stem)
    value = value.replace("_", "")
    value = re.sub(r"[()\[\]{}]", "", value)
    value = re.sub(r"\s+", "", value)
    return value.lower()


def build_pdf_inventory(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pdf_path in sorted(root.rglob("*.pdf")):
        if not pdf_path.is_file():
            continue
        stat = pdf_path.stat()
        rel_path = pdf_path.relative_to(root)
        rows.append(
            {
                "relative_path": str(rel_path).replace("/", "\\"),
                "name": pdf_path.name,
                "normalized_name": normalize_filename(pdf_path.name),
                "parent": str(rel_path.parent).replace("/", "\\"),
                "size_bytes": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            }
        )
    return rows


def collect_problem_index_paths(problem_index: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for subject, subject_data in problem_index.get("subjects", {}).items():
        for relative_path in subject_data.get("textbook_files", []):
            rows.append(
                {
                    "subject": subject,
                    "relative_path": relative_path,
                    "name": Path(relative_path).name,
                    "normalized_name": normalize_filename(Path(relative_path).name),
                }
            )
    return rows


def summarize_matches(
    inventory: list[dict[str, Any]],
    problem_index_paths: list[dict[str, str]],
    chunk_source_names: list[str],
) -> dict[str, Any]:
    inventory_by_rel = {row["relative_path"] for row in inventory}
    inventory_by_name = defaultdict(list)
    inventory_by_normalized = defaultdict(list)
    duplicate_name_groups: dict[str, list[str]] = {}

    for row in inventory:
        inventory_by_name[row["name"]].append(row["relative_path"])
        inventory_by_normalized[row["normalized_name"]].append(row["relative_path"])

    for name, paths in inventory_by_name.items():
        if len(paths) > 1:
            duplicate_name_groups[name] = paths

    exact_path_match_count = 0
    exact_name_match_count = 0
    normalized_name_match_count = 0
    unmatched_problem_index_paths: list[dict[str, Any]] = []

    for row in problem_index_paths:
        rel_path = row["relative_path"]
        name = row["name"]
        normalized_name = row["normalized_name"]

        path_exists = rel_path in inventory_by_rel
        name_matches = inventory_by_name.get(name, [])
        normalized_matches = inventory_by_normalized.get(normalized_name, [])

        if path_exists:
            exact_path_match_count += 1
        if name_matches:
            exact_name_match_count += 1
        if normalized_matches:
            normalized_name_match_count += 1
        if not path_exists:
            unmatched_problem_index_paths.append(
                {
                    "subject": row["subject"],
                    "registered_path": rel_path,
                    "registered_name": name,
                    "exact_name_matches": name_matches,
                    "normalized_name_matches": normalized_matches[:10],
                }
            )

    chunk_exact_name_matches = 0
    chunk_normalized_name_matches = 0
    unmatched_chunk_sources: list[dict[str, Any]] = []
    for name in chunk_source_names:
        exact_name_matches = inventory_by_name.get(name, [])
        normalized_name_matches = inventory_by_normalized.get(normalize_filename(name), [])
        if exact_name_matches:
            chunk_exact_name_matches += 1
        if normalized_name_matches:
            chunk_normalized_name_matches += 1
        if not exact_name_matches:
            unmatched_chunk_sources.append(
                {
                    "source_name": name,
                    "exact_name_matches": exact_name_matches,
                    "normalized_name_matches": normalized_name_matches[:10],
                }
            )

    return {
        "inventory": {
            "total_pdfs": len(inventory),
            "unique_names": len(inventory_by_name),
            "duplicate_name_groups": len(duplicate_name_groups),
            "duplicate_name_samples": dict(list(duplicate_name_groups.items())[:50]),
        },
        "problem_index": {
            "registered_paths": len(problem_index_paths),
            "exact_path_matches": exact_path_match_count,
            "exact_name_matches": exact_name_match_count,
            "normalized_name_matches": normalized_name_match_count,
            "unmatched_count": len(unmatched_problem_index_paths),
            "unmatched_samples": unmatched_problem_index_paths[:100],
        },
        "chunks_index": {
            "source_names": len(chunk_source_names),
            "exact_name_matches": chunk_exact_name_matches,
            "normalized_name_matches": chunk_normalized_name_matches,
            "unmatched_count": len(unmatched_chunk_sources),
            "unmatched_samples": unmatched_chunk_sources[:100],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a canonical PDF manifest from the workspace")
    parser.add_argument(
        "--output",
        help="Output JSON path. Default: .agent/state/workspace_pdf_manifest_<today>.json",
    )
    args = parser.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")
    output_path = Path(args.output) if args.output else STATE_DIR / f"workspace_pdf_manifest_{today}.json"

    inventory = build_pdf_inventory(ROOT)
    problem_index = load_json(PROBLEM_INDEX_PATH, {})
    chunks_index = load_json(CHUNKS_INDEX_PATH, {})
    problem_index_paths = collect_problem_index_paths(problem_index)
    chunk_source_names = [row.get("file") for row in chunks_index.get("sources", []) if row.get("file")]

    manifest = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "workspace_root": str(ROOT),
        "files": inventory,
        "summary": summarize_matches(inventory, problem_index_paths, chunk_source_names),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"output={output_path}")
    print(f"total_pdfs={manifest['summary']['inventory']['total_pdfs']}")
    print(f"problem_index_exact_path_matches={manifest['summary']['problem_index']['exact_path_matches']}")
    print(f"problem_index_exact_name_matches={manifest['summary']['problem_index']['exact_name_matches']}")
    print(f"problem_index_normalized_name_matches={manifest['summary']['problem_index']['normalized_name_matches']}")
    print(f"chunks_exact_name_matches={manifest['summary']['chunks_index']['exact_name_matches']}")
    print(f"chunks_normalized_name_matches={manifest['summary']['chunks_index']['normalized_name_matches']}")


if __name__ == "__main__":
    main()
