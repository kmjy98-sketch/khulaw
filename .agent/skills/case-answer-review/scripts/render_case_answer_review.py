#!/usr/bin/env python3
"""사례답안 초벌 채점 + 대비자료 패킷 생성기."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

_p = os.path.abspath(__file__)
while os.path.basename(_p) != ".agent" and os.path.dirname(_p) != _p:
    _p = os.path.dirname(_p)
sys.path.insert(0, os.path.join(_p, "scripts"))
from _vault import VAULT_ROOT, vp  # noqa: E402


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(VAULT_ROOT)
STATE_DIR = ROOT / ".agent" / "state"
SKILL_DIR = ROOT / ".agent" / "skills" / "case-answer-review"
DEFAULT_PACKET = STATE_DIR / "case_answer_packet.json"
CASE_INDEX = STATE_DIR / "case_material_index.json"
TEXTBOOK_CANDIDATES = STATE_DIR / "textbook_problem_candidates.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf", "-q"])
        from pypdf import PdfReader

    reader = PdfReader(str(path))
    chunks: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            chunks.append(f"--- Page {index} ---\n{page_text}")
    return "\n\n".join(chunks)


def read_docx(path: Path) -> str:
    paragraphs: list[str] = []
    with zipfile.ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for para in root.findall(".//w:p", namespace):
        texts = [node.text for node in para.findall(".//w:t", namespace) if node.text]
        if texts:
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


def load_answer_text(input_path: str | None, inline_text: str | None) -> tuple[str, str]:
    if inline_text:
        return inline_text, "inline-text"
    if not input_path:
        return "", "미제공"

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"답안 파일을 찾을 수 없습니다: {path}")

    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ""}:
        return read_text_file(path), str(path)
    if suffix == ".pdf":
        return read_pdf(path), str(path)
    if suffix == ".docx":
        return read_docx(path), str(path)

    return "", str(path)


def load_source_payload(input_path: str | None, inline_text: str | None, label: str) -> dict[str, Any]:
    text, source = load_answer_text(input_path, inline_text)
    normalized = normalize_text(text)
    return {
        "label": label,
        "text": text,
        "normalized": normalized,
        "source": source,
        "provided": bool(normalized),
    }


def build_source_payload_from_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_paths = [Path(path) for path in record.get("extract_md", [])]
    if record.get("path"):
        candidate_paths.append(Path(record["path"]))

    for path in candidate_paths:
        if not path.exists():
            continue
        if path.suffix.lower() not in {".md", ".txt", ".pdf", ".docx", ""}:
            continue
        text, source = load_answer_text(str(path), None)
        normalized = normalize_text(text)
        if normalized:
            return {
                "label": label,
                "text": text,
                "normalized": normalized,
                "source": source,
                "provided": True,
                "auto_selected": True,
            }

    return {
        "label": label,
        "text": "",
        "normalized": "",
        "source": "미제공",
        "provided": False,
        "auto_selected": False,
    }


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def infer_subject(subject_arg: str | None, progress: dict, problem_index: dict, answer_source: str) -> str:
    if subject_arg:
        return subject_arg

    textbook = progress.get("current_scope", {}).get("textbook", "")
    candidates = list(problem_index.get("subjects", {}).keys())
    for candidate in candidates:
        if candidate in textbook or candidate in answer_source:
            return candidate
    return candidates[0] if candidates else "민법"


def query_topics_by_lecture(subject_data: dict, lecture: int) -> list[dict]:
    results = []
    for topic_name, topic_data in subject_data.get("topics", {}).items():
        topic_lecture = topic_data.get("lecture", 0)
        if isinstance(topic_lecture, list):
            match = lecture in topic_lecture
        else:
            match = topic_lecture == lecture
        if match:
            record = dict(topic_data)
            record["topic_name"] = topic_name
            results.append(record)
    return results


def tokenize_scope(value: str) -> list[str]:
    return [token for token in re.split(r"[_>\s,/()\-\[\]]+", value) if len(token) >= 2]


def resolve_topics(subject_data: dict, topic_query: str | None, lecture: int | None, learning: dict) -> list[dict]:
    if lecture is not None:
        return query_topics_by_lecture(subject_data, lecture)

    topics = subject_data.get("topics", {})
    scope_text = topic_query or learning.get("current_scope", "")
    query_tokens = tokenize_scope(scope_text)

    scored: list[tuple[int, dict]] = []
    for topic_name, topic_data in topics.items():
        score = 0
        if topic_query:
            if topic_query == topic_name:
                score += 10
            if topic_query in topic_name or topic_name in topic_query:
                score += 6
        for token in query_tokens:
            if token in topic_name:
                score += 4
            if any(token in keyword or keyword in token for keyword in topic_data.get("keywords", [])):
                score += 2
        if score > 0:
            record = dict(topic_data)
            record["topic_name"] = topic_name
            scored.append((score, record))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:5]]


def classify_material(path_str: str) -> str:
    value = path_str.lower()
    if "기출" in path_str or "모의답안" in path_str or "모범답안" in path_str or "우수답안" in path_str:
        return "기출/답안"
    if "(1-" in value or "교재" in path_str:
        return "교재"
    if "사례" in path_str or "사례연습" in path_str:
        return "사례자료"
    if "(4-" in value or "dt" in value or "선택" in path_str:
        return "선택형"
    if "(2-" in value or "정리" in path_str:
        return "정리"
    return "기타"


def summarize_corpus(subject_data: dict) -> tuple[str, dict]:
    files = subject_data.get("textbook_files", [])
    grouped: dict[str, list[str]] = defaultdict(list)
    for file_path in files:
        grouped[classify_material(file_path)].append(file_path)

    lines = [f"- 총 인식 자료 수: {len(files)}"]
    payload = {"total": len(files), "grouped": grouped}
    for category, items in grouped.items():
        lines.append(f"- {category}: {len(items)}개")
        preview = items[:5]
        for item in preview:
            lines.append(f"  - {item}")
    return "\n".join(lines), payload


def unique_problem_items(items: list[dict]) -> list[dict]:
    seen = set()
    output = []
    for item in items:
        key = (item.get("id"), item.get("file"), item.get("question_num"))
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def match_textbook_candidates(candidate_index: dict, subject: str, topics: list[dict]) -> list[dict]:
    topic_names = {topic.get("topic_name") for topic in topics if topic.get("topic_name")}
    matched: list[dict] = []
    for item in candidate_index.get("candidates", []):
        if item.get("subject") != subject:
            continue
        topic_matches = item.get("topic_matches", [])
        if any(match.get("topic") in topic_names for match in topic_matches if isinstance(match, dict)):
            matched.append(item)
    return unique_problem_items(matched)


def collect_problems(topics: list[dict]) -> dict:
    case_items: list[dict] = []
    dt_items: list[dict] = []
    textbook_items: list[dict] = []
    for topic in topics:
        problems = topic.get("problems", {})
        case_items.extend(problems.get("case", []))
        dt_items.extend(problems.get("dt", []))
        textbook_items.extend(problems.get("textbook", []))
    case_items = unique_problem_items(case_items)
    dt_items = unique_problem_items(dt_items)
    textbook_items = unique_problem_items(textbook_items)
    return {"case": case_items, "dt": dt_items, "textbook": textbook_items}


def render_problem_summary(problems: dict, case_bundles: list[dict] | None = None) -> str:
    lines = [
        f"- 사례형 문제: {len(problems['case'])}개",
        f"- 선택형 문제: {len(problems['dt'])}개",
        f"- 교재 내 문제 후보: {len(problems['textbook'])}개",
    ]
    if case_bundles:
        lines.append("- 자동 매칭된 사례형 묶음:")
        for bundle in case_bundles[:4]:
            files = bundle.get("files", {})
            lines.append(
                "  - "
                f"{bundle.get('bundle_key', '미상')} | "
                f"question={len(files.get('question', []))}, "
                f"explanation={len(files.get('explanation', []))}, "
                f"grading={len(files.get('grading', []))}, "
                f"model_answer={len(files.get('model_answer', []))}"
            )
    for item in problems["case"][:8]:
        lines.append(f"  - 사례: {item.get('file', '미상')} | 해설: {item.get('answer_source', '미상')}")
    for item in problems["dt"][:8]:
        preview = item.get("question_preview", "")
        lines.append(
            f"  - 선택형: {item.get('file', '미상')} Q{item.get('question_num', '?')} | 정답: {item.get('answer', '미상')} | 미리보기: {preview[:40]}"
        )
    for item in problems["textbook"][:8]:
        preview = item.get("question_preview") or item.get("question_text", "")
        page = item.get("page") or item.get("page_span_hint", "미상")
        source_name = item.get("file") or item.get("source_pdf", "미상")
        lines.append(
            "  - "
            f"교재문제: {source_name} | 유형: {item.get('problem_type', '미상')} | "
            f"페이지: {page} | 미리보기: {preview[:40]}"
        )
    return "\n".join(lines)


def collect_alignment_refs(topics: list[dict], alignment: dict) -> list[dict]:
    concept_map = alignment.get("concepts", {})
    results = []
    topic_names = [topic["topic_name"] for topic in topics]
    for concept_name, data in concept_map.items():
        for topic_name in topic_names:
            if concept_name == topic_name or concept_name in topic_name or topic_name in concept_name:
                for book_name, book_info in data.items():
                    if book_name == "keywords":
                        continue
                    results.append(
                        {
                            "concept": concept_name,
                            "book_name": book_name,
                            "book_code": book_info.get("book_code", ""),
                            "pages": book_info.get("pages", []),
                            "keywords": data.get("keywords", []),
                        }
                    )
                break
    return results


def collect_tag_refs(topics: list[dict], tag_index: dict) -> dict:
    keyword_sources: dict[str, list[str]] = {}
    article_hits: set[str] = set()
    case_hits: set[str] = set()
    for topic in topics:
        for keyword in topic.get("keywords", []):
            sources = tag_index.get("keywords", {}).get(keyword, [])
            if sources:
                keyword_sources[keyword] = sources
                for source in sources:
                    source_data = tag_index.get("sources", {}).get(source, {})
                    article_hits.update(source_data.get("articles", []))
                    case_hits.update(source_data.get("cases", []))
    return {
        "keyword_sources": keyword_sources,
        "articles": sorted(article_hits),
        "cases": sorted(case_hits),
    }


def normalize_lecture_values(topics: list[dict], lecture_hint: int | None) -> set[int]:
    lectures: set[int] = set()
    if lecture_hint is not None:
        lectures.add(lecture_hint)
    for topic in topics:
        lecture = topic.get("lecture")
        if isinstance(lecture, list):
            lectures.update(item for item in lecture if isinstance(item, int))
        elif isinstance(lecture, int):
            lectures.add(lecture)
    return lectures


def match_case_bundles(case_index: dict, topics: list[dict], lecture_hint: int | None) -> list[dict]:
    lectures = normalize_lecture_values(topics, lecture_hint)
    bundles = case_index.get("bundles", [])
    if lectures:
        matched = [bundle for bundle in bundles if bundle.get("round_hint") in lectures]
    else:
        matched = bundles[:5]
    return matched[:5]


def autofill_payload(existing: dict[str, Any], bundles: list[dict], kind: str, label: str) -> dict[str, Any]:
    if existing["provided"]:
        existing["auto_selected"] = False
        return existing

    for bundle in bundles:
        for record in bundle.get("files", {}).get(kind, []):
            payload = build_source_payload_from_record(record, label)
            if payload["provided"]:
                payload["bundle_key"] = bundle.get("bundle_key", "")
                return payload

    existing["auto_selected"] = False
    return existing


def search_exam_candidates(untyped_entries: list[dict], answer_source: str, subject: str, topics: list[dict]) -> list[str]:
    tokens = tokenize_scope(Path(answer_source).stem if answer_source not in {"미제공", "inline-text"} else "")
    tokens.append(subject)
    for topic in topics:
        tokens.append(topic["topic_name"])
        tokens.extend(topic.get("keywords", [])[:3])

    unique_tokens = [token for token in dict.fromkeys(tokens) if len(token) >= 2]
    scored: list[tuple[int, str]] = []

    for entry in untyped_entries:
        path_value = entry.get("path", "")
        if not path_value:
            continue
        if not any(mark in path_value for mark in ["기출", "모의답안", "모범답안", "우수답안", "채점평"]):
            continue

        score = 0
        for token in unique_tokens:
            if token in path_value:
                score += 1
        if "내신" in path_value:
            score += 2
        if "기출" in path_value:
            score += 2
        if score > 0:
            scored.append((score, path_value))

    scored.sort(key=lambda item: item[0], reverse=True)
    seen = set()
    results = []
    for _, path_value in scored:
        if path_value in seen:
            continue
        seen.add(path_value)
        results.append(path_value)
        if len(results) >= 15:
            break
    return results


def parse_page_span(value: Any) -> tuple[int, int] | None:
    if isinstance(value, list):
        numbers = [int(item) for item in value if isinstance(item, int)]
        if numbers:
            return min(numbers), max(numbers)
    if isinstance(value, str):
        numbers = [int(item) for item in re.findall(r"\d+", value)]
        if numbers:
            return min(numbers), max(numbers)
    return None


def page_gap(left: tuple[int, int] | None, right: tuple[int, int] | None) -> int | None:
    if not left or not right:
        return None
    if left[1] < right[0]:
        return right[0] - left[1]
    if right[1] < left[0]:
        return left[0] - right[1]
    return 0


def discover_related_issues(topics: list[dict], subject_data: dict, alignment: dict, lecture_hint: int | None) -> list[dict]:
    if not topics:
        return []

    selected_names = {topic["topic_name"] for topic in topics}
    selected_keywords = {keyword for topic in topics for keyword in topic.get("keywords", [])}
    selected_lectures = normalize_lecture_values(topics, lecture_hint)
    selected_anchor = topics[0]["topic_name"]
    selected_page = next((parse_page_span(topic.get("pages")) for topic in topics if parse_page_span(topic.get("pages"))), None)

    concept_map = alignment.get("concepts", {})
    related: list[dict] = []
    for topic_name, topic_data in subject_data.get("topics", {}).items():
        if topic_name in selected_names:
            continue

        reasons: list[str] = []
        score = 0

        lecture = topic_data.get("lecture")
        if isinstance(lecture, list):
            lecture_overlap = selected_lectures.intersection(item for item in lecture if isinstance(item, int))
        elif isinstance(lecture, int):
            lecture_overlap = {lecture} if lecture in selected_lectures else set()
        else:
            lecture_overlap = set()

        if lecture_overlap:
            score += 4
            reasons.append(f"같은 회차 {', '.join(str(item) for item in sorted(lecture_overlap))}")

        overlap_keywords = sorted(set(topic_data.get("keywords", [])).intersection(selected_keywords))
        if overlap_keywords:
            score += min(4, len(overlap_keywords))
            reasons.append(f"공통 키워드 {', '.join(overlap_keywords[:3])}")

        gap = page_gap(selected_page, parse_page_span(topic_data.get("pages")))
        if gap is not None and gap <= 15:
            score += 3
            reasons.append("교재 인접 페이지")

        alignment_refs: list[str] = []
        for concept_name, data in concept_map.items():
            if concept_name == topic_name or concept_name in topic_name or topic_name in concept_name:
                for book_name, book_info in data.items():
                    if book_name == "keywords":
                        continue
                    pages = book_info.get("pages", [])
                    if pages:
                        alignment_refs.append(f"{book_name} p.{pages[0]}-{pages[-1]}")
                break
        if alignment_refs:
            score += 1

        if score <= 0 or not reasons:
            continue

        related.append(
            {
                "topic_name": topic_name,
                "lecture": lecture,
                "pages": topic_data.get("pages", "미상"),
                "keywords": topic_data.get("keywords", [])[:6],
                "reasons": reasons,
                "alignment_refs": alignment_refs[:3],
                "score": score,
                "selected_anchor": selected_anchor,
            }
        )

    related.sort(key=lambda item: (-item["score"], item["topic_name"]))
    return related[:6]


def build_required_points(topics: list[dict], tag_refs: dict, alignment_refs: list[dict]) -> list[str]:
    points: list[str] = []
    for topic in topics:
        points.append(topic["topic_name"])
        points.extend(topic.get("keywords", [])[:5])
    points.extend(tag_refs.get("articles", [])[:5])
    for item in alignment_refs:
        points.extend(item.get("keywords", [])[:3])
    unique = []
    seen = set()
    for point in points:
        if not point or point in seen:
            continue
        seen.add(point)
        unique.append(point)
    return unique[:15]


def provisional_grade(answer_text: str, required_points: list[str], weak_points: list[str]) -> dict:
    if not answer_text:
        return {
            "grade": "보류",
            "coverage": 0.0,
            "covered": [],
            "missing": required_points[:8],
            "weak_overlap": [],
        }

    normalized = answer_text.lower()
    covered = [point for point in required_points if point.lower() in normalized]
    missing = [point for point in required_points if point not in covered]

    coverage = len(covered) / len(required_points) if required_points else 0.0
    if coverage >= 0.6 and len(answer_text) >= 300:
        grade = "O"
    elif coverage >= 0.25 and len(answer_text) >= 120:
        grade = "△"
    else:
        grade = "X"

    weak_overlap = [item for item in weak_points if any(token in item for token in missing + covered)]
    return {
        "grade": grade,
        "coverage": round(coverage, 2),
        "covered": covered,
        "missing": missing,
        "weak_overlap": weak_overlap,
    }


def split_text_units(text: str) -> list[str]:
    units = re.split(r"(?:\n{2,}|(?<=[.!?])\s+)", text)
    return [normalize_text(unit) for unit in units if normalize_text(unit)]


def build_excerpt(text: str, needle: str | None = None, limit: int = 110) -> str:
    normalized = normalize_text(text)
    if not normalized:
        return ""

    if needle:
        index = normalized.lower().find(needle.lower())
    else:
        index = -1

    if index < 0:
        return normalized[:limit] + ("..." if len(normalized) > limit else "")

    start = max(0, index - 35)
    end = min(len(normalized), index + len(needle) + 45)
    excerpt = normalized[start:end]
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(normalized):
        excerpt = excerpt + "..."
    return excerpt


def format_source_location(label: str, source: str) -> str:
    if source == "inline-text":
        return f"{label} inline-text (확인 불가—위치 식별자 부족)"
    if source == "미제공":
        return "자료 부족—보류"
    return source


def find_text_evidence(point: str, payload: dict[str, Any]) -> dict[str, str] | None:
    if not payload["provided"] or point.lower() not in payload["normalized"].lower():
        return None

    for unit in split_text_units(payload["text"]):
        if point.lower() in unit.lower():
            return {
                "kind": payload["label"],
                "quote": build_excerpt(unit, point),
                "location": format_source_location(payload["label"], payload["source"]),
            }

    return {
        "kind": payload["label"],
        "quote": build_excerpt(payload["text"], point),
        "location": format_source_location(payload["label"], payload["source"]),
    }


def find_rag_evidence(point: str, rag_results: list[dict]) -> dict[str, str] | None:
    for item in rag_results:
        text = item.get("text", "")
        if point.lower() not in text.lower():
            continue

        location_parts = [item.get("source_file") or "RAG"]
        if item.get("page") not in {"", None}:
            location_parts.append(f"p.{item['page']}")
        if item.get("chapter"):
            location_parts.append(str(item["chapter"]))
        if item.get("chunk_id"):
            location_parts.append(str(item["chunk_id"]))
        return {
            "kind": "교재RAG",
            "quote": build_excerpt(text, point),
            "location": " ".join(location_parts),
        }
    return None


def analyze_consistency(
    required_points: list[str],
    answer_payload: dict[str, Any],
    question_payload: dict[str, Any],
    model_payload: dict[str, Any],
    explanation_payload: dict[str, Any],
    rag_results: list[dict],
    rag_status: str,
) -> dict[str, Any]:
    supported: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    reference_points: list[str] = []

    for point in required_points:
        in_answer = point.lower() in answer_payload["normalized"].lower()
        question_hit = find_text_evidence(point, question_payload)
        model_hit = find_text_evidence(point, model_payload)
        explanation_hit = find_text_evidence(point, explanation_payload)
        textbook_hit = find_rag_evidence(point, rag_results)

        reference_hits = [hit for hit in [model_hit, explanation_hit, textbook_hit] if hit]
        if reference_hits:
            record = {
                "point": point,
                "supports": [hit["kind"] for hit in reference_hits],
                "question_anchor": bool(question_hit),
                "evidence": reference_hits[0],
            }
            reference_points.append(point)
            if in_answer:
                supported.append(record)
            else:
                missing.append(record)

        if model_hit and not (explanation_hit or textbook_hit):
            pending.append(
                {
                    "point": point,
                    "evidence": model_hit,
                }
            )

    coverage = len(supported) / len(reference_points) if reference_points else 0.0
    if not (model_payload["provided"] or explanation_payload["provided"] or rag_results):
        status = "자료 부족—보류"
    elif not reference_points:
        status = "자료 부족—보류"
    elif coverage >= 0.7 and not missing:
        status = "일치 높음"
    elif coverage >= 0.35:
        status = "부분 일치"
    else:
        status = "일치 낮음"

    if model_payload["provided"] and not (explanation_payload["provided"] or rag_results):
        status = f"{status} / 교재·해설 검증 제한"

    return {
        "status": status,
        "coverage": round(coverage, 2),
        "sources": {
            "question": question_payload["provided"],
            "model_answer": model_payload["provided"],
            "explanation": explanation_payload["provided"],
        },
        "rag_status": rag_status,
        "supported": supported,
        "missing": missing,
        "pending": pending,
    }


def render_consistency_summary(review: dict[str, Any]) -> str:
    lines = [
        f"- 검토 상태: {review['status']}",
        (
            "- 입력 자료: "
            f"질문지={'제공' if review['sources']['question'] else '미제공'}, "
            f"모범답안={'제공' if review['sources']['model_answer'] else '미제공'}, "
            f"해설지={'제공' if review['sources']['explanation'] else '미제공'}, "
            f"교재RAG={review['rag_status']}"
        ),
        f"- 검토 커버리지: {review['coverage']}",
    ]

    if review["supported"]:
        lines.append("- 일치 포인트:")
        for item in review["supported"][:4]:
            lines.append(f"  - {item['point']} | 연결: {', '.join(item['supports'])}")
            lines.append(f'    - 근거 발췌: "{item["evidence"]["quote"]}"')
            lines.append(f"    - 근거 위치: 《{item['evidence']['location']}》")
    else:
        lines.append("- 일치 포인트: 자료 부족—보류")

    if review["missing"]:
        lines.append("- 누락 포인트:")
        for item in review["missing"][:4]:
            lines.append(f"  - {item['point']} | 연결: {', '.join(item['supports'])}")
            lines.append(f'    - 근거 발췌: "{item["evidence"]["quote"]}"')
            lines.append(f"    - 근거 위치: 《{item['evidence']['location']}》")
    else:
        lines.append("- 누락 포인트: 없음")

    if review["pending"]:
        lines.append("- 모답 연결 후 교재·해설 검증 보류:")
        for item in review["pending"][:4]:
            lines.append(f"  - {item['point']}")
            lines.append(f'    - 근거 발췌: "{item["evidence"]["quote"]}"')
            lines.append(f"    - 근거 위치: 《{item['evidence']['location']}》")
    else:
        lines.append("- 모답 연결 후 교재·해설 검증 보류: 없음")

    return "\n".join(lines)


def normalize_choice_entries(raw_choices: Any) -> list[str]:
    if not isinstance(raw_choices, list):
        return []

    choices: list[str] = []
    for entry in raw_choices:
        if isinstance(entry, dict):
            text = entry.get("text", "")
        else:
            text = str(entry)
        normalized = normalize_text(text)
        if normalized:
            choices.append(normalized)
        if len(choices) >= 5:
            break
    return choices[:5]


def parse_choice_statements(question_text: str) -> list[str]:
    normalized = normalize_text(re.split(r"해설|정답", question_text, maxsplit=1)[0])
    if "①" not in normalized or "..." in normalized:
        return []

    parts = re.split(r"(①|②|③|④|⑤)", normalized)
    if len(parts) < 5:
        return []

    choices: list[str] = []
    for index in range(1, len(parts), 2):
        if index + 1 >= len(parts):
            continue
        content = re.split(r"정답", parts[index + 1], maxsplit=1)[0]
        content = normalize_text(content)
        if not content:
            continue
        choices.append(content)
        if len(choices) >= 5:
            break
    return choices[:5]


def build_objective_ox(problems: dict) -> dict[str, Any]:
    direct_ox: list[dict[str, Any]] = []
    converted: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    markers = "①②③④⑤"

    for item in problems.get("dt", []):
        preview = normalize_text(item.get("question_text") or item.get("question_preview", ""))
        answer = item.get("answer")
        question_type = item.get("question_type")

        if question_type == "ox" or answer in {"O", "X"}:
            direct_ox.append(
                {
                    "file": item.get("file", "미상"),
                    "question_num": item.get("question_num", "?"),
                    "answer": answer,
                    "statement": build_excerpt(preview, limit=100),
                }
            )
            continue

        if not isinstance(answer, int):
            continue

        choices = normalize_choice_entries(item.get("choices"))
        if not choices:
            choices = parse_choice_statements(item.get("question_text", ""))

        if choices and len(choices) >= answer:
            converted_choices = []
            for index, choice in enumerate(choices, start=1):
                marker = markers[index - 1] if index <= len(markers) else str(index)
                converted_choices.append(
                    {
                        "marker": marker,
                        "statement": choice,
                        "answer": "O" if index == answer else "X",
                    }
                )
            converted.append(
                {
                    "file": item.get("file", "미상"),
                    "question_num": item.get("question_num", "?"),
                    "choices": converted_choices,
                }
            )
        else:
            pending.append(
                {
                    "file": item.get("file", "미상"),
                    "question_num": item.get("question_num", "?"),
                    "preview": build_excerpt(preview, limit=90),
                    "reason": "선지 원문 부족",
                }
            )

    return {
        "counts": {
            "direct_ox": len(direct_ox),
            "converted_choice": len(converted),
            "pending_choice": len(pending),
        },
        "direct_ox": direct_ox,
        "converted_choice": converted,
        "pending_choice": pending,
    }


def render_objective_ox_summary(ox_data: dict[str, Any]) -> str:
    counts = ox_data["counts"]
    lines = [
        f"- 직접 O/X 문제: {counts['direct_ox']}개",
        f"- 선지별 O/X 변환 완료: {counts['converted_choice']}개",
        f"- 선지 원문 부족 보류: {counts['pending_choice']}개",
    ]

    if ox_data["direct_ox"]:
        lines.append("- 바로 활용 가능한 O/X:")
        for item in ox_data["direct_ox"][:6]:
            lines.append(
                f"  - {item['file']} Q{item['question_num']} | 정답: {item['answer']} | 진술: {item['statement']}"
            )
    else:
        lines.append("- 바로 활용 가능한 O/X: 자료 부족—보류")

    if ox_data["converted_choice"]:
        lines.append("- 선지별 O/X 변환:")
        for item in ox_data["converted_choice"][:2]:
            lines.append(f"  - {item['file']} Q{item['question_num']}")
            for choice in item["choices"][:5]:
                lines.append(f"    - {choice['marker']} {choice['statement']} -> {choice['answer']}")
    else:
        lines.append("- 선지별 O/X 변환: 자료 부족—보류")

    if ox_data["pending_choice"]:
        lines.append("- 보류된 숫자선지:")
        for item in ox_data["pending_choice"][:5]:
            lines.append(
                f"  - {item['file']} Q{item['question_num']} | {item['reason']} | {item['preview']}"
            )
    else:
        lines.append("- 보류된 숫자선지: 없음")

    return "\n".join(lines)


def scan_problem_capabilities(problem_index: dict, learning: dict, case_index: dict | None = None) -> dict[str, Any]:
    stats = {
        "case_total": 0,
        "case_with_question": 0,
        "case_with_answer": 0,
        "case_bundle_count": case_index.get("bundle_count", 0) if case_index else 0,
        "dt_total": 0,
        "dt_ox": 0,
        "dt_choice": 0,
        "dt_choice_structured": 0,
        "dt_choice_convertible": 0,
        "textbook_total": 0,
        "textbook_with_question": 0,
        "learning_fields": list(learning.keys()),
    }

    for subject_data in problem_index.get("subjects", {}).values():
        for topic_data in subject_data.get("topics", {}).values():
            for item in topic_data.get("problems", {}).get("case", []):
                if not isinstance(item, dict):
                    continue
                stats["case_total"] += 1
                if item.get("question_text"):
                    stats["case_with_question"] += 1
                if item.get("answer"):
                    stats["case_with_answer"] += 1

            for item in topic_data.get("problems", {}).get("dt", []):
                if not isinstance(item, dict):
                    continue
                stats["dt_total"] += 1
                answer = item.get("answer")
                if item.get("question_type") == "ox" or answer in {"O", "X"}:
                    stats["dt_ox"] += 1
                    continue

                stats["dt_choice"] += 1
                choices = normalize_choice_entries(item.get("choices"))
                if choices:
                    stats["dt_choice_structured"] += 1
                    stats["dt_choice_convertible"] += 1
                    continue

                parsed = parse_choice_statements(item.get("question_text", ""))
                if parsed:
                    stats["dt_choice_convertible"] += 1

            for item in topic_data.get("problems", {}).get("textbook", []):
                if not isinstance(item, dict):
                    continue
                stats["textbook_total"] += 1
                if item.get("question_text"):
                    stats["textbook_with_question"] += 1

    return stats


def render_needs_summary(capabilities: dict[str, Any]) -> str:
    lines = [
        (
            "- 사례형 인덱스 현황: "
            f"총 {capabilities['case_total']}개, question_text 저장 {capabilities['case_with_question']}개, "
            f"answer 저장 {capabilities['case_with_answer']}개"
        ),
        (
            "- 선택형 인덱스 현황: "
            f"총 {capabilities['dt_total']}개, 직접 O/X {capabilities['dt_ox']}개, "
            f"숫자선지 {capabilities['dt_choice']}개, choices 저장 {capabilities['dt_choice_structured']}개"
        ),
        (
            "- 교재문제 인덱스 현황: "
            f"총 {capabilities['textbook_total']}개, question_text 저장 {capabilities['textbook_with_question']}개"
        ),
        f"- 사례형 묶음 인덱스: {capabilities['case_bundle_count']}개 번들",
        f"- learning.json 확인 필드: {', '.join(capabilities['learning_fields']) if capabilities['learning_fields'] else '자료 부족—보류'}",
    ]

    if capabilities["case_with_question"] == 0 or capabilities["case_with_answer"] == 0:
        lines.append("- 조사 판단: 질문지/모범답안/채점포인트 파일이 없으면 사례형 issue 단위 정밀 채점은 자료 부족—보류")
    else:
        lines.append("- 조사 판단: 사례형 정밀 채점에 필요한 최소 문항 메타데이터는 확보됨")

    blocked_choices = capabilities["dt_choice"] - capabilities["dt_choice_convertible"]
    if blocked_choices > 0:
        lines.append(f"- 조사 판단: 숫자선지 {blocked_choices}개는 선지 원문 부족으로 선지별 O/X 변환이 보류됨")
    else:
        lines.append("- 조사 판단: 숫자선지는 현재 자료만으로도 선지별 O/X 변환 가능")

    lines.append("- 조사 판단: 문항별 오답 이력 필드는 소스에서 확인할 수 없습니다. 누적 약점 유형화는 자료 부족—보류")
    return "\n".join(lines)


def rag_search(queries: list[str], skip_rag: bool) -> tuple[list[dict], str]:
    """qmd CLI 기반 RAG 검색 (LanceDB 대체, 2026-04-10)."""
    if skip_rag:
        return [], "skip-rag"

    qmd_lib_path = ROOT / ".agent" / "lib"
    if str(qmd_lib_path) not in sys.path:
        sys.path.insert(0, str(qmd_lib_path))

    try:
        from qmd_search import qmd_search, QmdSearchError  # type: ignore
    except Exception as exc:  # pragma: no cover
        return [], f"import-failed: {exc}"

    all_results = []
    seen = set()
    try:
        for query in queries[:3]:
            try:
                hits = qmd_search(query, k=4, mode="search")
            except QmdSearchError as exc:
                return [], f"search-failed: {exc}"
            for item in hits:
                key = item.get("docid") or item.get("path")
                if not key or key in seen:
                    continue
                seen.add(key)
                path = item.get("path", "")
                all_results.append(
                    {
                        "query": query,
                        "chunk_id": item.get("docid", ""),
                        "book_code": Path(path).stem if path else "",
                        "source_file": path,
                        "page": "",
                        "chapter": item.get("title", ""),
                        "text": normalize_text(item.get("snippet", ""))[:260],
                    }
                )
                if len(all_results) >= 6:
                    return all_results, "ok"
    except Exception as exc:  # pragma: no cover
        return [], f"search-failed: {exc}"

    return all_results, "ok"


def topic_summary(topics: list[dict]) -> str:
    if not topics:
        return "- 자료 부족—보류"
    lines = []
    for topic in topics:
        lines.append(
            f"- {topic['topic_name']} | 회차: {topic.get('lecture', '미상')} | 페이지: {topic.get('pages', '미상')} | 키워드: {', '.join(topic.get('keywords', [])[:8])}"
        )
    return "\n".join(lines)


def render_related_issue_summary(related_issues: list[dict]) -> str:
    if not related_issues:
        return "- 자료 부족—보류"

    lines = []
    for item in related_issues:
        lines.append(
            f"- {item['topic_name']} | 연결사유: {', '.join(item['reasons'])} | 페이지: {item['pages']} | 키워드: {', '.join(item['keywords'])}"
        )
        lines.append(
            f'  - 근거 발췌: "{item["topic_name"]} | 회차: {item["lecture"]} | 페이지: {item["pages"]} | 키워드: {", ".join(item["keywords"])}"'
        )
        lines.append(f"  - 근거 위치: 《.agent/state/problem_index.json》 subjects.민법.topics.{item['topic_name']}")
        lines.append(f'  - 근거 발췌: "{item["selected_anchor"]}와 같은 회차/교재 범위에서 함께 검토된 후보"')
        lines.append(f"  - 근거 위치: 《.agent/state/problem_index.json》 subjects.민법.topics.{item['selected_anchor']}")
        if item["alignment_refs"]:
            lines.append(f"  - 교재 참조: {', '.join(item['alignment_refs'])}")
    return "\n".join(lines)


def authority_summary(tag_refs: dict, alignment_refs: list[dict], rag_results: list[dict], exam_candidates: list[str]) -> str:
    lines = []
    if tag_refs["articles"]:
        lines.append(f"- 관련 조문: {', '.join(tag_refs['articles'][:12])}")
    else:
        lines.append("- 관련 조문: 자료 부족—보류")

    if tag_refs["cases"]:
        lines.append(f"- 관련 판례: {', '.join(tag_refs['cases'][:10])}")
    else:
        lines.append("- 관련 판례: 소스에서 확인할 수 없습니다")

    if alignment_refs:
        lines.append("- 교재 페이지 참조:")
        for item in alignment_refs[:8]:
            pages = item.get("pages", [])
            page_text = f"{pages[0]}-{pages[-1]}" if pages else "미상"
            lines.append(f"  - {item['concept']} -> {item['book_name']} ({item['book_code']}) p.{page_text}")

    if rag_results:
        lines.append("- RAG 설명 청크:")
        for item in rag_results[:8]:
            lines.append(
                f"  - [{item['query']}] {item['source_file']} p.{item['page']} {item['chapter']} | \"{item['text']}\""
            )
    else:
        lines.append("- RAG 설명 청크: 자료 부족—보류")

    if exam_candidates:
        lines.append("- 내신/기출 후보 파일:")
        for item in exam_candidates[:10]:
            lines.append(f"  - {item}")

    return "\n".join(lines)


def grading_summary(grade: dict) -> str:
    lines = [
        f"- 초벌 평정: {grade['grade']}",
        f"- 키워드 커버리지: {grade['coverage']}",
        f"- 포착된 포인트: {', '.join(grade['covered'][:10]) if grade['covered'] else '자료 부족—보류'}",
        f"- 누락 포인트: {', '.join(grade['missing'][:10]) if grade['missing'] else '없음'}",
    ]
    return "\n".join(lines)


def weakness_summary(grade: dict, learning: dict) -> str:
    lines = []
    existing = learning.get("weak_points", [])
    overlap = grade.get("weak_overlap", [])
    new_candidates = [item for item in grade.get("missing", []) if item not in existing][:8]

    lines.append(f"- 기존 약점 수: {len(existing)}")
    lines.append(f"- 중첩 약점: {', '.join(overlap[:8]) if overlap else '없음'}")
    lines.append(f"- 신규 약점 후보: {', '.join(new_candidates) if new_candidates else '없음'}")
    return "\n".join(lines)


def next_steps(grade: dict, problems: dict) -> str:
    lines = []
    if grade["grade"] == "X":
        lines.append("- 해당 쟁점의 교재 페이지와 사례형 해설을 먼저 다시 읽는다.")
        lines.append("- 사례형 문제 1개와 선택형 문제 3개 이상을 바로 재풀이한다.")
    elif grade["grade"] == "△":
        lines.append("- 누락 포인트 중심으로 답안 구조를 다시 써본다.")
        lines.append("- 관련 사례형 해설과 선택형 선지 근거를 비교한다.")
    else:
        lines.append("- 답안 구조는 유지하되 누락 포인트가 없는지 다시 체크한다.")

    if problems["case"]:
        lines.append("- 관련 사례형 문제 해설 파일부터 우선 검토한다.")
    if problems["dt"]:
        lines.append("- 관련 선택형 문제를 근거 확인용으로 병행한다.")
    if problems["textbook"]:
        lines.append("- 교재 내부 문제 후보를 같이 열어 쟁점 배열과 문항 유형을 대조한다.")
    lines.append("- 중요 누락 포인트는 learning.json 약점 후보로 검토한다.")
    return "\n".join(lines)


def render_template(template: str, variables: dict[str, str]) -> str:
    output = template
    for key, value in variables.items():
        output = output.replace(f"{{{{{key}}}}}", value)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="사례답안 초벌 채점 + 대비자료 패킷 생성")
    parser.add_argument("input_path", nargs="?", help="답안 파일 경로(pdf/docx/txt/md)")
    parser.add_argument("--text", help="직접 전달할 답안 본문")
    parser.add_argument("--question-path", help="질문지 파일 경로(pdf/docx/txt/md)")
    parser.add_argument("--question-text", help="질문지 본문")
    parser.add_argument("--model-answer-path", help="모범답안 파일 경로(pdf/docx/txt/md)")
    parser.add_argument("--model-answer-text", help="모범답안 본문")
    parser.add_argument("--explanation-path", help="해설지 파일 경로(pdf/docx/txt/md)")
    parser.add_argument("--explanation-text", help="해설지 본문")
    parser.add_argument("--subject", help="과목명")
    parser.add_argument("--topic", help="쟁점명")
    parser.add_argument("--lecture", type=int, help="회차")
    parser.add_argument("--output", "-o", help="마크다운 출력 경로")
    parser.add_argument("--packet-output", default=str(DEFAULT_PACKET), help="패킷 JSON 출력 경로")
    parser.add_argument("--skip-rag", action="store_true", help="RAG 검색 생략")
    args = parser.parse_args()

    answer_payload = load_source_payload(args.input_path, args.text, "답안")
    question_payload = load_source_payload(args.question_path, args.question_text, "질문지")
    model_payload = load_source_payload(args.model_answer_path, args.model_answer_text, "모범답안")
    explanation_payload = load_source_payload(args.explanation_path, args.explanation_text, "해설지")
    answer_text = answer_payload["text"]
    answer_source = answer_payload["source"]
    normalized_answer = answer_payload["normalized"]

    progress = load_json(STATE_DIR / "progress.json", {})
    learning = load_json(STATE_DIR / "learning.json", {})
    problem_index = load_json(STATE_DIR / "problem_index.json", {})
    alignment = load_json(STATE_DIR / "alignment.json", {})
    curriculum = load_json(STATE_DIR / "curriculum.json", {})
    tag_index = load_json(STATE_DIR / "tag_index.json", {})
    untyped_files = load_json(STATE_DIR / "untyped_files.json", [])
    case_index = load_json(CASE_INDEX, {})
    textbook_candidate_index = load_json(TEXTBOOK_CANDIDATES, {})

    subject = infer_subject(args.subject, progress, problem_index, answer_source)
    subject_data = problem_index.get("subjects", {}).get(subject, {})
    if not subject_data:
        raise ValueError(f"problem_index.json에서 과목을 찾을 수 없습니다: {subject}")

    topics = resolve_topics(subject_data, args.topic, args.lecture, learning)
    case_bundles = match_case_bundles(case_index, topics, args.lecture)
    question_payload = autofill_payload(question_payload, case_bundles, "question", "질문지")
    model_payload = autofill_payload(model_payload, case_bundles, "model_answer", "모범답안")
    explanation_payload = autofill_payload(explanation_payload, case_bundles, "explanation", "해설지")
    problems = collect_problems(topics)
    textbook_candidates = match_textbook_candidates(textbook_candidate_index, subject, topics)
    problems["textbook"] = unique_problem_items(problems.get("textbook", []) + textbook_candidates)
    corpus_text, corpus_payload = summarize_corpus(subject_data)
    alignment_refs = collect_alignment_refs(topics, alignment)
    tag_refs = collect_tag_refs(topics, tag_index)
    exam_candidates = search_exam_candidates(untyped_files, answer_source, subject, topics)
    related_issues = discover_related_issues(topics, subject_data, alignment, args.lecture)
    required_points = build_required_points(topics, tag_refs, alignment_refs)
    grade = provisional_grade(normalized_answer, required_points, learning.get("weak_points", []))

    retrieval_queries = [topic["topic_name"] for topic in topics]
    for topic in topics:
        retrieval_queries.extend(topic.get("keywords", [])[:4])
    retrieval_queries.extend(grade.get("missing", [])[:5])
    rag_results, rag_status = rag_search(list(dict.fromkeys(retrieval_queries)), args.skip_rag)
    consistency = analyze_consistency(
        required_points,
        answer_payload,
        question_payload,
        model_payload,
        explanation_payload,
        rag_results,
        rag_status,
    )
    objective_ox = build_objective_ox(problems)
    capabilities = scan_problem_capabilities(problem_index, learning, case_index)

    packet = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "subject": subject,
        "scope": {"topic": args.topic, "lecture": args.lecture},
        "answer_source": answer_source,
        "question_source": question_payload["source"],
        "model_answer_source": model_payload["source"],
        "explanation_source": explanation_payload["source"],
        "current_scope": progress.get("current_scope", {}),
        "learning_scope": learning.get("current_scope", ""),
        "topics": topics,
        "matched_case_bundles": case_bundles,
        "recognized_corpus": corpus_payload,
        "problems": problems,
        "alignment_refs": alignment_refs,
        "tag_refs": tag_refs,
        "exam_candidates": exam_candidates,
        "related_issues": related_issues,
        "required_points": required_points,
        "grading": grade,
        "rag_status": rag_status,
        "rag_results": rag_results,
        "consistency_review": consistency,
        "objective_ox": objective_ox,
        "capability_scan": capabilities,
        "curriculum_primary_book": curriculum.get("primary_book", ""),
    }

    packet_path = Path(args.packet_output)
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

    template = (SKILL_DIR / "templates" / "case_answer_review.md").read_text(encoding="utf-8")
    variables = {
        "generated_at": packet["generated_at"],
        "subject": subject,
        "answer_source": answer_source,
        "scope_label": args.topic or (f"lecture {args.lecture}" if args.lecture is not None else learning.get("current_scope", "미지정")),
        "current_scope": json.dumps(progress.get("current_scope", {}), ensure_ascii=False),
        "packet_path": str(packet_path),
        "corpus_summary": corpus_text,
        "topic_summary": topic_summary(topics),
        "related_issue_summary": render_related_issue_summary(related_issues),
        "grading_summary": grading_summary(grade),
        "consistency_summary": render_consistency_summary(consistency),
        "objective_ox_summary": render_objective_ox_summary(objective_ox),
        "problem_summary": render_problem_summary(problems, case_bundles),
        "authority_summary": authority_summary(tag_refs, alignment_refs, rag_results, exam_candidates),
        "weakness_summary": weakness_summary(grade, learning),
        "needs_summary": render_needs_summary(capabilities),
        "next_steps": next_steps(grade, problems),
        "disclaimer": (
            "현재 결과는 워크스페이스 자료와 키워드/RAG 기반의 초벌 검토다. "
            "질문지, 배점표, 모범답안, 해설지가 함께 들어오면 정밀 채점과 선지별 O/X 변환 정확도가 올라간다."
        ),
    }
    report = render_template(template, variables)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"보고서 저장됨: {output_path}")
    else:
        print(report)

    print(f"패킷 저장됨: {packet_path}")


if __name__ == "__main__":
    main()
