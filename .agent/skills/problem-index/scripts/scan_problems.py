#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


ALLOWED_SUFFIXES = {".pdf", ".md", ".txt"}
PROBLEM_KINDS = ("dt", "case", "textbook")
ANSWER_KEYWORDS = ("해설", "채점평", "모범답안")


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


def load_index() -> tuple[dict[str, Any] | None, Path]:
    index_path = get_problem_index_path()
    if not index_path.exists():
        print(f"인덱스 파일이 없습니다: {index_path}")
        return None, index_path
    with open(index_path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle), index_path


def save_index(index: dict[str, Any], index_path: Path) -> None:
    index["version"] = "2.0"
    index["last_updated"] = str(date.today())
    with open(index_path, "w", encoding="utf-8") as handle:
        json.dump(index, handle, ensure_ascii=False, indent=2)


def detect_subject(file_path: Path) -> str | None:
    path_text = str(file_path)
    # 민사소송법 · 민사집행법: 민법·민사 이전에 선검사
    if "민사소송" in path_text or "민소" in path_text:
        return "민사소송법"
    if "민사집행" in path_text or "민집" in path_text:
        return "민사집행법"
    if "민법" in path_text or "민사" in path_text:
        return "민법"
    # 형사소송법: 형법·형사 이전에 선검사
    if "형사소송" in path_text or "형소" in path_text:
        return "형사소송법"
    if "형법총론" in path_text or "총론" in path_text:
        return "형법총론"
    if "형법각론" in path_text or "각론" in path_text:
        return "형법각론"
    if "형법" in path_text or "형사" in path_text:
        return "형법총론"
    if "헌법" in path_text:
        return "헌법"
    if "행정법" in path_text:
        return "행정법"
    return None


def detect_problem_type(filename: str) -> str | None:
    if any(keyword in filename for keyword in ANSWER_KEYWORDS):
        return None
    if "_(사례)" in filename or "사례" in filename:
        return "case"
    if "_(선택)" in filename or "선택형" in filename or "DT" in filename:
        return "dt"
    if "_(교재)" in filename or "교재" in filename or "정리" in filename:
        return "textbook"

    if filename.startswith("(1-") or filename.startswith("(2-"):
        return "textbook"
    if filename.startswith("(3-"):
        return "case"
    if filename.startswith("(4-"):
        return "dt"
    return None


def lecture_matches(topic_lecture: Any, lecture: int) -> bool:
    if isinstance(topic_lecture, list):
        return lecture in topic_lecture
    return topic_lecture == lecture


def extract_lecture(filename: str) -> int | None:
    patterns = [
        r"DT[_\s-]*(\d+)회",
        r"DT[_\s-]*(\d+)차",
        r"\((\d+)-",
        r"(\d+)회",
        r"(\d+)차",
    ]
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def find_answer_file(problem_file: Path, all_files: list[Path]) -> Path | None:
    stem = problem_file.stem
    base_candidates = [stem]
    if "문제" in stem:
        base_candidates = [
            stem.replace("문제", replacement)
            for replacement in ("해설", "채점평", "모범답안")
        ]

    for candidate_stem in base_candidates:
        for other in all_files:
            if other == problem_file or other.suffix.lower() != problem_file.suffix.lower():
                continue
            if other.stem == candidate_stem:
                return other
    return None


def create_problem_entry(file_path: str, answer_source: str | None = None) -> dict[str, Any]:
    return {
        "file": file_path,
        "answer": None,
        "answer_source": answer_source,
        "verified": False,
        "last_verified": None,
    }


def is_registered(items: list[Any], file_path: str) -> bool:
    for item in items:
        if isinstance(item, str) and item == file_path:
            return True
        if isinstance(item, dict) and item.get("file") == file_path:
            return True
    return False


def match_topics(topics: dict[str, Any], filename: str, lecture: int | None) -> list[str]:
    matched: list[str] = []

    for topic_name, topic_data in topics.items():
        for keyword in topic_data.get("keywords", []):
            if keyword and keyword in filename:
                matched.append(topic_name)
                break

    if matched or lecture is None:
        return matched

    for topic_name, topic_data in topics.items():
        if lecture_matches(topic_data.get("lecture"), lecture):
            matched.append(topic_name)
    return matched


def ensure_problem_buckets(topic_data: dict[str, Any]) -> dict[str, list[Any]]:
    problems = topic_data.get("problems")
    if not isinstance(problems, dict):
        problems = {}
    for problem_kind in PROBLEM_KINDS:
        problems.setdefault(problem_kind, [])
    topic_data["problems"] = problems
    return problems


def scan_directory(dir_path: Path, index: dict[str, Any], workspace_root: Path | None, dry_run: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    all_files = [path for path in dir_path.rglob("*") if path.is_file()]

    for file_path in all_files:
        if file_path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue

        subject = detect_subject(file_path)
        problem_type = detect_problem_type(file_path.name)
        if subject is None or problem_type is None:
            continue

        subject_data = index.get("subjects", {}).get(subject)
        if not isinstance(subject_data, dict):
            continue

        answer_file = find_answer_file(file_path, all_files)
        file_ref = workspace_relative(file_path, workspace_root)
        answer_ref = workspace_relative(answer_file, workspace_root) if answer_file else None
        lecture = extract_lecture(file_path.name)
        topics = subject_data.get("topics", {})
        matched_topics = match_topics(topics, file_path.name, lecture)

        if not matched_topics and problem_type == "textbook":
            results.append(
                {
                    "file": file_ref,
                    "subject": subject,
                    "topic": "COMMON",
                    "type": problem_type,
                    "answer_source": answer_ref,
                }
            )
            if not dry_run:
                textbook_files = subject_data.get("textbook_files", [])
                if file_ref not in textbook_files:
                    textbook_files.append(file_ref)
                    subject_data["textbook_files"] = textbook_files
            continue

        for topic_name in matched_topics:
            results.append(
                {
                    "file": file_ref,
                    "subject": subject,
                    "topic": topic_name,
                    "type": problem_type,
                    "answer_source": answer_ref,
                }
            )
            if dry_run:
                continue

            topic_data = topics[topic_name]
            problems = ensure_problem_buckets(topic_data)
            if not is_registered(problems[problem_type], file_ref):
                problems[problem_type].append(create_problem_entry(file_ref, answer_ref))

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="문제 파일 스캔 및 인덱스 등록")
    parser.add_argument("--dir", "-d", type=str, default=".", help="스캔할 디렉터리")
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 결과만 출력")
    args = parser.parse_args()

    workspace_root = find_workspace_root()
    index, index_path = load_index()
    if index is None:
        return

    dir_path = Path(args.dir)
    if not dir_path.exists():
        print(f"디렉터리가 없습니다: {dir_path}")
        return

    results = scan_directory(dir_path, index, workspace_root, args.dry_run)
    print(f"[스캔 결과] {len(results)}건")
    print("=" * 50)
    for result in results:
        print(f"{result['type'].upper()}: {result['file']}")
        print(f"  -> {result['subject']} / {result['topic']}")
        if result.get("answer_source"):
            print(f"  -> answer: {result['answer_source']}")

    if args.dry_run:
        print("[DRY-RUN] problem_index.json은 변경하지 않았습니다.")
        return

    if results:
        save_index(index, index_path)
        print(f"[저장 완료] {index_path}")


if __name__ == "__main__":
    main()
