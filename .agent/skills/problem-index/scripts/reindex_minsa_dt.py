#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from extract_problems import create_problem_entries, extract_text_by_page, find_problems_and_answers  # type: ignore


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


def workspace_root_or_raise() -> Path:
    workspace_root = find_workspace_root()
    if workspace_root is None:
        raise FileNotFoundError("워크스페이스 루트를 찾지 못했습니다.")
    return workspace_root


def problem_index_path(workspace_root: Path) -> Path:
    return workspace_root / ".agent" / "state" / "problem_index.json"


def default_source_dir(workspace_root: Path) -> Path:
    return workspace_root / "1.민사" / "송영곤_기본민법" / "강의자료" / "선택형"


def default_log_path(workspace_root: Path) -> Path:
    return workspace_root / ".agent" / "state" / "dt_reindex_log.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def infer_lecture(path: Path) -> int | None:
    patterns = [
        r"DT[_\s-]*(\d+)회",
        r"DT[_\s-]*(\d+)차",
        r"\((\d+)-",
        r"(\d+)회",
        r"(\d+)차",
    ]
    for pattern in patterns:
        match = re.search(pattern, path.stem, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def is_question_pdf(path: Path) -> bool:
    if path.suffix.lower() != ".pdf":
        return False
    if any(keyword in path.name for keyword in ANSWER_KEYWORDS):
        return False
    return "DT" in path.name or "선택형" in path.name


def lecture_match(value: Any, lecture: int) -> bool:
    if isinstance(value, list):
        return lecture in value
    return value == lecture


def replace_entries(index: dict[str, Any], lecture: int, entries: list[dict[str, Any]], source_path: str) -> list[str]:
    subject_data = index.get("subjects", {}).get("민법", {})
    updated_topics: list[str] = []
    for topic_name, topic_data in subject_data.get("topics", {}).items():
        if not lecture_match(topic_data.get("lecture"), lecture):
            continue

        problems = topic_data.setdefault("problems", {"dt": [], "case": [], "textbook": []})
        filtered = []
        for item in problems.get("dt", []):
            if isinstance(item, dict) and item.get("source_path") == source_path:
                continue
            filtered.append(item)

        filtered.extend(entries)
        problems["dt"] = filtered
        topic_data["problems"] = problems
        updated_topics.append(topic_name)
    return updated_topics


def build_entries(source_pdf: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pages = extract_text_by_page(str(source_pdf))
    problems = find_problems_and_answers(pages)
    entries = create_problem_entries(problems, str(source_pdf))
    summary = {
        "pages": len(pages),
        "problem_count": len(entries),
        "ox_count": sum(1 for entry in entries if entry.get("answer") in {"O", "X"}),
        "choice_count": sum(1 for entry in entries if isinstance(entry.get("answer"), int)),
    }
    return entries, summary


def main() -> None:
    workspace_root = workspace_root_or_raise()
    parser = argparse.ArgumentParser(description="민법 DT PDF 재인덱싱")
    parser.add_argument("--source-dir", default=str(default_source_dir(workspace_root)), help="원본 PDF 디렉터리")
    parser.add_argument("--log-output", default=str(default_log_path(workspace_root)), help="로그 JSON 경로")
    parser.add_argument("--dry-run", action="store_true", help="problem_index.json은 저장하지 않음")
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    pdfs = sorted(path for path in source_dir.rglob("*.pdf") if is_question_pdf(path))
    if not pdfs:
        raise FileNotFoundError(f"재인덱싱할 DT 문제 PDF가 없습니다: {source_dir}")

    index_path = problem_index_path(workspace_root)
    index = load_json(index_path, {})
    log: dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_dir": str(source_dir),
        "dry_run": args.dry_run,
        "processed_files": [],
    }

    for pdf in pdfs:
        lecture = infer_lecture(pdf)
        record: dict[str, Any] = {"source_pdf": str(pdf), "status": "pending"}
        if lecture is None:
            record["status"] = "skipped"
            record["reason"] = "lecture 추출 실패"
            log["processed_files"].append(record)
            continue

        entries, summary = build_entries(pdf)
        updated_topics = replace_entries(index, lecture, entries, str(pdf.resolve()))
        record.update(
            {
                "status": "ready" if args.dry_run else "updated",
                "lecture": lecture,
                "updated_topics": updated_topics,
                **summary,
            }
        )
        log["processed_files"].append(record)

    if not args.dry_run:
        index["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    log_path = Path(args.log_output)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"처리 파일 수: {len(log['processed_files'])}")
    print(f"로그 저장: {log_path}")
    if not args.dry_run:
        print(f"problem_index 저장: {index_path}")


if __name__ == "__main__":
    main()
