#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROBLEM_KINDS = ("dt", "case", "textbook")


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


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


def get_problem_index_path() -> Path:
    workspace_root = find_workspace_root()
    if workspace_root is not None:
        return workspace_root / ".agent" / "state" / "problem_index.json"
    return Path(".agent/state/problem_index.json")


def workspace_relative(path: Path, workspace_root: Path | None) -> str:
    resolved = path.resolve()
    if workspace_root is not None:
        try:
            return str(resolved.relative_to(workspace_root.resolve())).replace("/", "\\")
        except ValueError:
            pass
    return str(resolved)


def resolve_reference(value: Any, workspace_root: Path | None) -> str | None:
    if not isinstance(value, str) or not value:
        return None

    raw_path = value.split("#", 1)[0]
    if not raw_path:
        return None

    candidate = Path(raw_path)
    probes: list[Path] = []
    if candidate.is_absolute():
        probes.append(candidate)
    if workspace_root is not None:
        probes.append(workspace_root / raw_path)
    probes.append(candidate)

    for probe in probes:
        if probe.exists():
            return workspace_relative(probe, workspace_root)
    return None


def load_index() -> tuple[dict[str, Any] | None, Path]:
    index_path = get_problem_index_path()
    if not index_path.exists():
        print(f"인덱스 파일이 없습니다: {index_path}")
        return None, index_path
    with open(index_path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle), index_path


def normalize_item(item: Any, workspace_root: Path | None) -> dict[str, Any] | None:
    if isinstance(item, str):
        normalized: dict[str, Any] = {
            "file": item,
            "answer": None,
            "answer_source": None,
            "verified": False,
            "last_verified": None,
        }
    elif isinstance(item, dict):
        normalized = dict(item)
    else:
        return None

    if normalized.get("answer") is None:
        normalized["verified"] = False
        if "last_verified" in normalized:
            normalized["last_verified"] = None

    resolved_file = resolve_reference(normalized.get("source_path"), workspace_root)
    if resolved_file is None:
        resolved_file = resolve_reference(normalized.get("file"), workspace_root)
    normalized["path_exists"] = resolved_file is not None
    if resolved_file is not None:
        normalized["resolved_file"] = resolved_file

    resolved_answer = resolve_reference(normalized.get("answer_source"), workspace_root)
    if resolved_answer is not None:
        normalized["resolved_answer_source"] = resolved_answer

    return normalized


def normalize_problems(raw_problems: dict[str, Any], workspace_root: Path | None) -> dict[str, list[dict[str, Any]]]:
    normalized: dict[str, list[dict[str, Any]]] = {kind: [] for kind in PROBLEM_KINDS}
    for problem_kind in PROBLEM_KINDS:
        for item in raw_problems.get(problem_kind, []):
            normalized_item = normalize_item(item, workspace_root)
            if normalized_item is not None:
                normalized[problem_kind].append(normalized_item)
    return normalized


def lecture_matches(topic_lecture: Any, lecture: int) -> bool:
    if isinstance(topic_lecture, list):
        return lecture in topic_lecture
    return topic_lecture == lecture


def query_by_lecture(index: dict[str, Any], lecture: int, subject: str | None, workspace_root: Path | None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    subjects_to_search = [subject] if subject else list(index.get("subjects", {}).keys())

    for subject_name in subjects_to_search:
        subject_data = index.get("subjects", {}).get(subject_name)
        if not isinstance(subject_data, dict):
            continue

        for topic_name, topic_data in subject_data.get("topics", {}).items():
            if not lecture_matches(topic_data.get("lecture"), lecture):
                continue

            raw_problems = topic_data.get("problems", {})
            results.append(
                {
                    "subject": subject_name,
                    "topic": topic_name,
                    "toc_path": topic_data.get("toc_path", ""),
                    "pages": topic_data.get("pages", ""),
                    "keywords": topic_data.get("keywords", []),
                    "problems": normalize_problems(raw_problems, workspace_root),
                }
            )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="진도 기반 문제 조회")
    parser.add_argument("--lecture", "-l", type=int, required=True, help="진도 회차")
    parser.add_argument("--subject", "-s", type=str, default=None, help="과목명")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
    args = parser.parse_args()

    workspace_root = find_workspace_root()
    index, _ = load_index()
    if index is None:
        return

    results = query_by_lecture(index, args.lecture, args.subject, workspace_root)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not results:
        print(f"진도 {args.lecture}회차에 해당하는 항목이 없습니다.")
        return

    print(f"[진도 {args.lecture}회차]")
    print("=" * 50)
    for result in results:
        print(f"* {result['subject']} - {result['topic']}")
        print(f"  목차: {result['toc_path']}")
        print(f"  페이지: {result['pages']}")
        print(f"  키워드: {', '.join(result['keywords'])}")
        for problem_kind in PROBLEM_KINDS:
            items = result["problems"].get(problem_kind, [])
            resolved_count = sum(1 for item in items if item.get("path_exists"))
            print(f"  {problem_kind}: {len(items)}건 (resolved {resolved_count}건)")


if __name__ == "__main__":
    main()
