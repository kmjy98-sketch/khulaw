#!/usr/bin/env python3
"""Scan textbook extracts for embedded problem candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[4]
STATE_DIR = ROOT / ".agent" / "state"
EXTRACT_DIR = ROOT / ".agent" / "data" / "pdf_extracts"
CHUNKS_INDEX_PATH = EXTRACT_DIR / "chunks_index.json"
PROBLEM_INDEX_PATH = STATE_DIR / "problem_index.json"
ALIGNMENT_PATH = STATE_DIR / "alignment.json"
DEFAULT_OUTPUT = STATE_DIR / "textbook_problem_candidates.json"
DEFAULT_LOG = STATE_DIR / "textbook_problem_scan_log.json"
DEFAULT_OVERRIDE_PATH = STATE_DIR / "textbook_problem_topic_overrides.json"

PAGE_MARKER_RE = re.compile(r"^--- Page (\d+) ---\s*$")
BOOK_CODE_RE = re.compile(r"^(\d+-\d+)")
CASE_HEADING_RE = re.compile(r"^\s*사\s*례\s*\d+")
CASE_SUBHEADING_RE = re.compile(r"^\s*\d+\s*-\s*\d+\s*[.)]")
QUESTION_REF_RE = re.compile(r"제\s*\d+\s*문(?:의|제)?")
QUESTION_NUM_RE = re.compile(r"문제\s*\d+")
SCORE_RE = re.compile(r"배점\s*\d+\s*점")
OBJECTIVE_RE = re.compile(r"(옳은\s+것은|옳지\s+않은\s+것은|다음\s+중)")
CHOICE_MARKER_RE = re.compile(r"[①②③④⑤]")
WEAK_MARKER_RE = re.compile(r"(예시|설문|문제되는 경우)")
DOT_LEADER_RE = re.compile(r"[.·…]{4,}")
SANITIZE_RE = re.compile(r"[^0-9A-Za-z]+")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_topic_overrides(path: Path) -> list[dict[str, Any]]:
    raw = load_json(path, {})
    if not isinstance(raw, dict):
        return []

    items = raw.get("overrides", [])
    if not isinstance(items, list):
        return []

    overrides: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        source_pdf = str(item.get("source_pdf", "")).strip()
        topic = str(item.get("topic", "")).strip()
        action = str(item.get("action", "")).strip().lower()
        if not source_pdf:
            continue
        if action != "ignore" and not topic:
            continue

        page = item.get("page")
        try:
            page_num = int(page) if page is not None else None
        except (TypeError, ValueError):
            page_num = None

        overrides.append(
            {
                "source_pdf": source_pdf,
                "page": page_num,
                "subject": str(item.get("subject", "")).strip(),
                "topic": topic,
                "action": action,
                "match_text": str(item.get("match_text", "")).strip(),
                "reason": str(item.get("reason", "")).strip(),
            }
        )
    return overrides


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_excerpt(text: str, limit: int = 140) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."


def unique_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        candidate_id = item.get("id", "")
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        output.append(item)
    return output


def sanitize_token(value: str, limit: int = 80) -> str:
    token = SANITIZE_RE.sub("_", value).strip("_")
    return token[:limit] or "candidate"


def build_candidate_id(source_file: str, book_code: str, page_num: int, line_num: int) -> str:
    source_key = normalize_text(source_file) or "textbook"
    digest = hashlib.sha1(source_key.encode("utf-8")).hexdigest()[:10]
    code = sanitize_token(book_code or "tb", limit=12)
    return f"TB_{code}_{digest}_p{page_num:03d}_l{line_num:03d}"


def parse_pages(markdown_text: str) -> list[tuple[int, list[str]]]:
    pages: list[tuple[int, list[str]]] = []
    current_page: int | None = None
    current_lines: list[str] = []

    for raw_line in markdown_text.splitlines():
        page_match = PAGE_MARKER_RE.match(raw_line.strip())
        if page_match:
            if current_page is not None:
                pages.append((current_page, current_lines))
            current_page = int(page_match.group(1))
            current_lines = []
            continue
        current_lines.append(raw_line.rstrip())

    if current_page is not None:
        pages.append((current_page, current_lines))
    return pages


def is_toc_page(lines: list[str]) -> bool:
    header = " ".join(line.strip() for line in lines[:10])
    if "목 차" in header or "목차" in header:
        return True
    if "머리말" in header or "학습방법" in header or "보조교재" in header:
        return True
    dot_leaders = sum(1 for line in lines if DOT_LEADER_RE.search(line))
    return dot_leaders >= 4


def is_textbook_source(source_file: str, textbook_names: set[str]) -> bool:
    if "정리" in source_file or "가이드" in source_file:
        return False
    if "교재" in source_file:
        return True
    return source_file in textbook_names


def build_textbook_name_set(problem_index: dict[str, Any], subject_filter: str | None) -> set[str]:
    names: set[str] = set()
    for subject_name, subject_data in problem_index.get("subjects", {}).items():
        if subject_filter and subject_name != subject_filter:
            continue
        for path_str in subject_data.get("textbook_files", []):
            names.add(Path(path_str).name)
    return names


def build_alignment_entries(alignment: dict[str, Any], problem_index: dict[str, Any]) -> list[dict[str, Any]]:
    topic_lookup: dict[str, list[str]] = {}
    for subject_name, subject_data in problem_index.get("subjects", {}).items():
        topic_lookup[subject_name] = list(subject_data.get("topics", {}).keys())

    entries: list[dict[str, Any]] = []
    for concept_name, data in alignment.get("concepts", {}).items():
        topic_matches: list[tuple[str, str]] = []
        for subject_name, topic_names in topic_lookup.items():
            for topic_name in topic_names:
                if concept_name == topic_name or concept_name in topic_name or topic_name in concept_name:
                    topic_matches.append((subject_name, topic_name))

        for book_name, book_info in data.items():
            if book_name == "keywords":
                continue
            pages = [page for page in book_info.get("pages", []) if isinstance(page, int)]
            if not pages:
                continue
            entries.append(
                {
                    "concept": concept_name,
                    "book_name": book_name,
                    "book_code": book_info.get("book_code", ""),
                    "pages": pages,
                    "keywords": data.get("keywords", []),
                    "topic_matches": topic_matches,
                }
            )
    return entries


def build_subject_topic_entries(problem_index: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    entries: dict[str, list[dict[str, Any]]] = {}
    for subject_name, subject_data in problem_index.get("subjects", {}).items():
        subject_entries: list[dict[str, Any]] = []
        for topic_name, topic_data in subject_data.get("topics", {}).items():
            tokens = [topic_name]
            tokens.extend(keyword for keyword in topic_data.get("keywords", []) if isinstance(keyword, str))
            normalized_tokens = [token for token in dict.fromkeys(tokens) if len(token) >= 2]
            subject_entries.append(
                {
                    "subject": subject_name,
                    "topic": topic_name,
                    "keywords": normalized_tokens,
                }
            )
        entries[subject_name] = subject_entries
    return entries


def resolve_manual_override(
    overrides: list[dict[str, Any]],
    subject_topic_entries: dict[str, list[dict[str, Any]]],
    source_file: str,
    source_subject: str,
    book_code: str,
    page_num: int,
    candidate_label: str,
    question_text: str,
) -> dict[str, Any] | None:
    if not overrides:
        return None

    haystack = normalize_text(f"{candidate_label} {question_text}")
    for item in overrides:
        if item.get("source_pdf") != source_file:
            continue

        override_page = item.get("page")
        if override_page is not None and override_page != page_num:
            continue

        match_text = item.get("match_text", "")
        if match_text and match_text not in haystack:
            continue

        if item.get("action") == "ignore":
            return {
                "action": "ignore",
                "reason": item.get("reason", ""),
            }

        subject_name = item.get("subject") or source_subject
        topic_name = item.get("topic", "")
        topic_exists = any(
            entry.get("topic") == topic_name for entry in subject_topic_entries.get(subject_name, [])
        )
        if not topic_exists:
            continue

        keywords = [match_text] if match_text else []
        return {
            "subject": subject_name,
            "topic": topic_name,
            "concept": topic_name,
            "book_code": book_code,
            "page_gap": None,
            "match_strategy": "manual_override",
            "keywords": keywords,
            "reason": item.get("reason", ""),
        }
    return None


def infer_subject(source_file: str, problem_index: dict[str, Any], subject_filter: str | None) -> str:
    if subject_filter:
        return subject_filter
    for subject_name in problem_index.get("subjects", {}).keys():
        if subject_name in source_file:
            return subject_name
    return next(iter(problem_index.get("subjects", {}).keys()), "민법")


def score_line(line: str) -> tuple[int, list[str]]:
    score = 0
    signals: list[str] = []
    compact = normalize_text(line)

    if CASE_HEADING_RE.search(compact):
        score += 3
        signals.append("case_heading")
    if CASE_SUBHEADING_RE.search(compact):
        score += 2
        signals.append("case_subheading")
    if QUESTION_REF_RE.search(compact):
        score += 2
        signals.append("question_ref")
    if QUESTION_NUM_RE.search(compact):
        score += 1
        signals.append("question_number")
    if SCORE_RE.search(compact):
        score += 1
        signals.append("score")
    if OBJECTIVE_RE.search(compact):
        score += 2
        signals.append("objective_prompt")
    if CHOICE_MARKER_RE.search(compact):
        score += 1
        signals.append("choice_marker")
    if WEAK_MARKER_RE.search(compact):
        score += 1
        signals.append("weak_marker")

    return score, signals


def should_start_candidate(lines: list[str], index: int, min_score: int) -> tuple[bool, int, list[str]]:
    line = lines[index].strip()
    if not line or len(line) < 4:
        return False, 0, []
    score, signals = score_line(line)
    if score >= min_score:
        return True, score, signals

    if index + 1 < len(lines):
        next_score, next_signals = score_line(lines[index + 1].strip())
        if score + next_score >= min_score and next_score > 0:
            merged = list(dict.fromkeys(signals + next_signals))
            return True, score + next_score, merged
    return False, score, signals


def capture_block(lines: list[str], start_index: int) -> tuple[int, str]:
    collected: list[str] = []
    end_index = start_index

    for cursor in range(start_index, min(len(lines), start_index + 14)):
        line = lines[cursor].strip()
        if not line:
            if collected and len(collected) >= 4:
                end_index = cursor
                break
            continue

        if cursor > start_index:
            boundary_score, _ = score_line(line)
            if boundary_score >= 3 and len(normalize_text(" ".join(collected))) >= 180:
                end_index = cursor - 1
                break

        collected.append(line)
        end_index = cursor
        if len(normalize_text(" ".join(collected))) >= 800:
            break

    return end_index, normalize_text(" ".join(collected))


def classify_problem_type(text: str, signals: list[str]) -> str:
    if "objective_prompt" in signals or ("choice_marker" in signals and "question_ref" in signals):
        return "objective"
    if "case_heading" in signals or "case_subheading" in signals or "question_ref" in signals or "score" in signals:
        return "case"
    if "weak_marker" in signals:
        return "example"
    return "unknown"


def classify_confidence(score: int, text: str) -> str:
    if score >= 4 and len(text) >= 80:
        return "high"
    if score >= 3 and len(text) >= 40:
        return "medium"
    return "low"


def extract_question_label(text: str) -> str:
    first_sentence = re.split(r"[:\[\]]", text, maxsplit=1)[0]
    return build_excerpt(first_sentence, limit=80)


def match_topics(
    alignment_entries: list[dict[str, Any]],
    subject_topic_entries: dict[str, list[dict[str, Any]]],
    subject_name: str,
    book_code: str,
    page_num: int,
    max_gap: int,
    question_text: str,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for entry in alignment_entries:
        if entry.get("book_code") != book_code:
            continue
        pages = entry.get("pages", [])
        if not pages:
            continue

        page_gap = min(abs(page_num - page) for page in pages)
        if page_gap > max_gap:
            continue

        topic_candidates = entry.get("topic_matches") or [(subject_name, entry.get("concept", ""))]
        for matched_subject, topic_name in topic_candidates:
            key = (matched_subject, topic_name)
            if key in seen:
                continue
            seen.add(key)
            matches.append(
                {
                    "subject": matched_subject,
                    "topic": topic_name,
                    "concept": entry.get("concept", ""),
                    "book_code": book_code,
                    "page_gap": page_gap,
                    "match_strategy": "alignment",
                    "keywords": entry.get("keywords", [])[:8],
                }
            )

    matches.sort(key=lambda item: (item["page_gap"], item["subject"], item["topic"]))
    if matches:
        return matches[:5]

    fallback: list[dict[str, Any]] = []
    normalized_question = normalize_text(question_text)
    title_zone = normalized_question[:100]
    front_text = normalized_question[:200]
    for topic_entry in subject_topic_entries.get(subject_name, []):
        score = 0
        for token in topic_entry.get("keywords", []):
            if not token:
                continue
            if token in title_zone:
                score += 6 if token == topic_entry["topic"] else 4
                continue
            if token in front_text:
                score += 3 if token == topic_entry["topic"] else 2
        if score <= 0:
            continue
        fallback.append(
            {
                "subject": subject_name,
                "topic": topic_entry["topic"],
                "concept": topic_entry["topic"],
                "book_code": book_code,
                "page_gap": None,
                "match_score": score,
                "match_strategy": "text",
                "keywords": topic_entry.get("keywords", [])[:8],
            }
        )

    fallback.sort(key=lambda item: (-item["match_score"], item["topic"]))
    return fallback[:5]


def scan_chunk(
    chunk_path: Path,
    source_file: str,
    source_subject: str,
    alignment_entries: list[dict[str, Any]],
    subject_topic_entries: dict[str, list[dict[str, Any]]],
    topic_overrides: list[dict[str, Any]],
    min_score: int,
    max_gap: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    markdown_text = chunk_path.read_text(encoding="utf-8")
    pages = parse_pages(markdown_text)
    book_code_match = BOOK_CODE_RE.match(chunk_path.stem)
    book_code = book_code_match.group(1) if book_code_match else ""

    chunk_candidates: list[dict[str, Any]] = []
    stats = {
        "chunk": chunk_path.name,
        "pages": len(pages),
        "candidates": 0,
        "manual_overrides": 0,
        "ignored_overrides": 0,
        "skipped_toc_pages": 0,
        "types": {"case": 0, "objective": 0, "example": 0, "unknown": 0},
    }

    for page_num, raw_lines in pages:
        lines = [line for line in raw_lines if line.strip()]
        if not lines:
            continue
        if is_toc_page(lines):
            stats["skipped_toc_pages"] += 1
            continue

        cursor = 0
        while cursor < len(lines):
            should_start, score, signals = should_start_candidate(lines, cursor, min_score)
            if not should_start:
                cursor += 1
                continue

            end_index, block_text = capture_block(lines, cursor)
            confidence = classify_confidence(score, block_text)
            if confidence == "low":
                cursor = max(end_index + 1, cursor + 1)
                continue

            problem_type = classify_problem_type(block_text, signals)
            topic_matches = match_topics(
                alignment_entries,
                subject_topic_entries,
                source_subject,
                book_code,
                page_num,
                max_gap,
                block_text,
            )
            primary_topic = topic_matches[0] if topic_matches else None
            candidate_label = extract_question_label(block_text)
            manual_override = resolve_manual_override(
                topic_overrides,
                subject_topic_entries,
                source_file,
                source_subject,
                book_code,
                page_num,
                candidate_label,
                block_text,
            )
            if manual_override is not None:
                if manual_override.get("action") == "ignore":
                    stats["manual_overrides"] += 1
                    stats["ignored_overrides"] += 1
                    cursor = max(end_index + 1, cursor + 1)
                    continue
                primary_topic = manual_override
                topic_matches = [manual_override]
                stats["manual_overrides"] += 1
            candidate_id = build_candidate_id(source_file, book_code, page_num, cursor + 1)

            chunk_candidates.append(
                {
                    "id": candidate_id,
                    "subject": source_subject,
                    "book_code": book_code,
                    "source_pdf": source_file,
                    "source_md": str(chunk_path),
                    "page": page_num,
                    "page_span_hint": str(page_num),
                    "problem_type": problem_type,
                    "question_label": candidate_label,
                    "question_text": block_text,
                    "question_preview": build_excerpt(block_text, limit=120),
                    "signals": signals,
                    "signal_score": score,
                    "confidence": confidence,
                    "status": "pending_db_registration" if primary_topic else "pending_topic_mapping",
                    "topic_matches": topic_matches,
                    "primary_topic": primary_topic,
                }
            )
            stats["candidates"] += 1
            stats["types"][problem_type] = stats["types"].get(problem_type, 0) + 1
            cursor = max(end_index + 1, cursor + 1)

    return chunk_candidates, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan textbook extracts for embedded problem candidates")
    parser.add_argument("--subject", help="Limit scan to one subject name")
    parser.add_argument("--min-score", type=int, default=3, help="Minimum signal score")
    parser.add_argument("--max-page-gap", type=int, default=4, help="Max alignment page gap")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Candidate manifest JSON path")
    parser.add_argument("--log-output", default=str(DEFAULT_LOG), help="Scan log JSON path")
    parser.add_argument("--override-file", default=str(DEFAULT_OVERRIDE_PATH), help="Manual topic override JSON path")
    args = parser.parse_args()

    chunks_index = load_json(CHUNKS_INDEX_PATH, {})
    problem_index = load_json(PROBLEM_INDEX_PATH, {})
    alignment = load_json(ALIGNMENT_PATH, {})
    textbook_names = build_textbook_name_set(problem_index, args.subject)
    alignment_entries = build_alignment_entries(alignment, problem_index)
    subject_topic_entries = build_subject_topic_entries(problem_index)
    topic_overrides = load_topic_overrides(Path(args.override_file))

    candidates: list[dict[str, Any]] = []
    log: dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "subject_filter": args.subject or "all",
        "min_score": args.min_score,
        "max_page_gap": args.max_page_gap,
        "override_file": args.override_file,
        "processed_sources": [],
        "totals": {
            "sources": 0,
            "chunks": 0,
            "pages": 0,
            "candidates": 0,
            "manual_overrides": 0,
            "pending_db_registration": 0,
            "pending_topic_mapping": 0,
            "by_type": {"case": 0, "objective": 0, "example": 0, "unknown": 0},
        },
    }

    for source_info in chunks_index.get("sources", []):
        source_file = source_info.get("file", "")
        if not source_file:
            continue
        if not is_textbook_source(source_file, textbook_names):
            continue

        source_subject = infer_subject(source_file, problem_index, args.subject)
        if args.subject and source_subject != args.subject:
            continue

        source_record = {
            "source_pdf": source_file,
            "subject": source_subject,
            "chunks": 0,
            "pages": 0,
            "candidates": 0,
            "manual_overrides": 0,
            "missing_chunks": [],
            "types": {"case": 0, "objective": 0, "example": 0, "unknown": 0},
        }

        log["totals"]["sources"] += 1
        for chunk_name in source_info.get("chunks", []):
            chunk_path = EXTRACT_DIR / chunk_name
            if not chunk_path.exists():
                source_record["missing_chunks"].append(chunk_name)
                continue

            chunk_candidates, chunk_stats = scan_chunk(
                chunk_path,
                source_file,
                source_subject,
                alignment_entries,
                subject_topic_entries,
                topic_overrides,
                args.min_score,
                args.max_page_gap,
            )
            candidates.extend(chunk_candidates)
            source_record["chunks"] += 1
            source_record["pages"] += chunk_stats["pages"]
            source_record["candidates"] += chunk_stats["candidates"]
            source_record["manual_overrides"] += chunk_stats.get("manual_overrides", 0)

            log["totals"]["chunks"] += 1
            log["totals"]["pages"] += chunk_stats["pages"]
            log["totals"]["candidates"] += chunk_stats["candidates"]
            log["totals"]["manual_overrides"] += chunk_stats.get("manual_overrides", 0)

            for problem_type, count in chunk_stats["types"].items():
                source_record["types"][problem_type] = source_record["types"].get(problem_type, 0) + count
                log["totals"]["by_type"][problem_type] = log["totals"]["by_type"].get(problem_type, 0) + count

        log["processed_sources"].append(source_record)

    candidates = unique_candidates(candidates)
    log["totals"]["candidates"] = len(candidates)
    log["totals"]["pending_db_registration"] = 0
    log["totals"]["pending_topic_mapping"] = 0
    log["totals"]["by_type"] = {"case": 0, "objective": 0, "example": 0, "unknown": 0}

    for candidate in candidates:
        status = candidate.get("status")
        if status in {"pending_db_registration", "pending_topic_mapping"}:
            log["totals"][status] += 1
        problem_type = candidate.get("problem_type", "unknown")
        log["totals"]["by_type"][problem_type] = log["totals"]["by_type"].get(problem_type, 0) + 1

    manifest = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "subject_filter": args.subject or "all",
        "candidate_count": len(candidates),
        "candidates": candidates,
    }

    output_path = Path(args.output)
    log_path = Path(args.log_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"교재 문제 후보: {len(candidates)}개")
    print(f"후보 저장: {output_path}")
    print(f"진행 로그: {log_path}")


if __name__ == "__main__":
    main()
