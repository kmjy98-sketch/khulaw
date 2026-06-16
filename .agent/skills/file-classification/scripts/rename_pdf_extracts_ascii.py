#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rename .agent/data/pdf_extracts markdown chunks to ASCII aliases while keeping
Korean citation titles in the source title registry.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[4]
MD_DIR = ROOT / ".agent" / "data" / "pdf_extracts"
REGISTRY_PATH = ROOT / ".agent" / "state" / "source_title_registry.json"
PLAN_PATH = ROOT / ".agent" / "state" / "pdf_extracts_ascii_rename_plan_2026-03-19.json"
LOG_PATH = ROOT / ".agent" / "state" / "pdf_extracts_ascii_rename_log_2026-03-19.json"
CHUNKS_INDEX_PATH = MD_DIR / "chunks_index.json"


SUBJECT_MAP = {
    "민법": "civ",
    "민사법": "cvl",
    "민사소송법": "csp",
    "헌법": "con",
    "형법": "crm",
    "형사소송법": "crp",
    "행정법": "adm",
    "국제법": "intl",
    "국제거래법": "itrd",
    "상법": "com",
    "친족상속": "fam",
    "가족법": "fam",
    "변호사": "bar",
}

INSTRUCTOR_MAP = {
    "송영곤": "song",
    "윤동환": "yoon",
    "곽낙규": "kwak",
    "박승수": "park",
    "홍영기": "hong",
    "홍형철": "honghc",
    "김기용": "kim",
    "강성민": "kang",
    "이주원": "lee",
    "송덕수": "songds",
    "양형우": "yang",
}

TERM_MAP = {
    "목차": "toc",
    "기본민강": "basic",
    "기본강의": "lec",
    "민법기본강의": "basiclec",
    "기본민법강의": "basiclec",
    "강의계획서": "plan",
    "진도표": "sched",
    "권리주체": "rights",
    "법률행위": "juract",
    "채권,계약": "oblctr",
    "계약각론": "contracts",
    "채권각론": "oblspec",
    "채권이행,불이행": "perform",
    "채권자지체,3자,변동": "creditor3p",
    "채권담보": "security",
    "물권총론,변동": "propertychg",
    "소유,점유": "ownposs",
    "친족,상속": "familysucc",
    "민법의맥기초": "civflowbase",
    "민법의맥": "civflow",
    "사례의맥": "caseflow",
    "사례연습": "cases",
    "필기노트": "notes",
    "선행학습가이드": "guide",
    "선행학습_가이드": "guide",
    "기초법리": "basics",
    "기록형": "record",
    "사례형": "case",
    "선택형": "mcq",
    "문제": "q",
    "해설": "ans",
    "채점기준표": "rubric",
    "정답표": "key",
}

NOISE_PATTERNS = [
    r"\(교재\)",
    r"\(정리\)",
    r"\(사례\)",
    r"\(선택\)",
    r"\(필기\)",
    r"\(총론\)",
    r"\(26\)",
    r"\(25\)",
]

INITIAL = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"]
MEDIAL = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"]
FINAL = ["", "k", "k", "ks", "n", "nj", "nh", "t", "l", "lk", "lm", "lb", "ls", "lt", "lp", "lh", "m", "p", "ps", "t", "t", "ng", "t", "t", "k", "t", "p", "h"]


@dataclass
class BasePlan:
    order: int
    base_stem: str
    citation_title: str
    book_code: str
    ascii_alias: str
    source_pdf: str


def strip_chunk_suffix(stem: str) -> str:
    stem = re.sub(r"_p\d{1,4}-\d{1,4}$", "", stem)
    stem = re.sub(r"_p\d{1,4}$", "", stem)
    return re.sub(r"_full$", "", stem)


def extract_page_suffix(stem: str) -> str:
    match = re.search(r"(_p\d{1,4}-\d{1,4}|_p\d{1,4}|_full)$", stem)
    return match.group(1) if match else ""


def extract_book_code(base_stem: str) -> str:
    match = re.match(r"(\d+-\d+)_(.+)$", base_stem)
    return match.group(1) if match else ""


def strip_code_prefix(base_stem: str) -> str:
    match = re.match(r"(\d+-\d+)_(.+)$", base_stem)
    return match.group(2) if match else base_stem


def romanize_char(ch: str) -> str:
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        syllable = code - 0xAC00
        return INITIAL[syllable // 588] + MEDIAL[(syllable % 588) // 28] + FINAL[syllable % 28]
    return ch


def romanize_text(text: str) -> str:
    text = "".join(romanize_char(ch) for ch in text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def compact_token(text: str, max_len: int = 12) -> str:
    token = romanize_text(text)
    return token[:max_len] if token else ""


def extract_year_token(text: str) -> str:
    for pattern in [r"\((\d{2})\)", r"(?<!\d)(20\d{2})(?!\d)", r"(?<!\d)(\d{2})대비", r"(?<!\d)(\d{2})년"]:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def remove_mapped_fragments(text: str, fragments: Iterable[str]) -> str:
    cleaned = text
    for fragment in fragments:
        if fragment:
            cleaned = cleaned.replace(fragment, " ")
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)
    cleaned = re.sub(r"[()\[\],.·]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def find_first_mapping(text: str, mapping: Dict[str, str]) -> Tuple[str, str]:
    for key in sorted(mapping, key=len, reverse=True):
        if key in text:
            return key, mapping[key]
    return "", ""


def build_ascii_alias(base_stem: str) -> Tuple[str, str, str]:
    book_code = extract_book_code(base_stem) or "src"
    title = strip_code_prefix(base_stem)
    subject_src, subject = find_first_mapping(title, SUBJECT_MAP)
    inst_src, instructor = find_first_mapping(title, INSTRUCTOR_MAP)

    matched_terms: List[str] = []
    term_values: List[str] = []
    residual = title
    for key in sorted(TERM_MAP, key=len, reverse=True):
        if key in residual:
            matched_terms.append(key)
            term_values.append(TERM_MAP[key])
            residual = residual.replace(key, " ")
        if len(term_values) >= 2:
            break

    year = extract_year_token(title)
    residual = remove_mapped_fragments(title, [subject_src, inst_src] + matched_terms)
    fallback_tokens = [compact_token(piece) for piece in re.split(r"[_\s-]+", residual) if piece]
    fallback_tokens = [token for token in fallback_tokens if token and not token.isdigit()]

    alias_parts = [subject or "src", book_code]
    if instructor:
        alias_parts.append(instructor)
    alias_parts.extend(term_values[:2])
    if year:
        alias_parts.append(year)
    for token in fallback_tokens:
        if token not in alias_parts:
            alias_parts.append(token)
        if len(alias_parts) >= 6:
            break

    alias = "_".join(alias_parts)
    alias = re.sub(r"_+", "_", alias).strip("_")
    return alias[:96], book_code, title


def load_existing_registry() -> Dict:
    if not REGISTRY_PATH.exists():
        return {"version": "1.0", "updated_at": "", "notes": [], "entries": []}
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def build_plan() -> Tuple[List[Dict], List[BasePlan]]:
    files = sorted(path for path in MD_DIR.glob("*.md") if path.name != "chunks_index.json")
    base_to_files: Dict[str, List[Path]] = defaultdict(list)
    for path in files:
        base_to_files[strip_chunk_suffix(path.stem)].append(path)

    alias_counts: Dict[str, int] = defaultdict(int)
    base_plans: List[BasePlan] = []
    file_plan: List[Dict] = []

    for order, base_stem in enumerate(sorted(base_to_files), 1):
        alias, book_code, citation_title = build_ascii_alias(base_stem)
        alias_counts[alias] += 1
        if alias_counts[alias] > 1:
            alias = f"{alias}_{alias_counts[alias]}"

        source_pdf = ""
        for file_path in base_to_files[base_stem]:
            page_suffix = extract_page_suffix(file_path.stem)
            new_name = f"{alias}{page_suffix}{file_path.suffix}"
            file_plan.append(
                {
                    "order": order,
                    "path": str(file_path),
                    "old_name": file_path.name,
                    "new_name": new_name,
                    "base_stem": base_stem,
                    "ascii_alias": alias,
                    "citation_title": citation_title,
                    "summary": f"{file_path.name} -> {new_name}",
                }
            )

        base_plans.append(
            BasePlan(
                order=order,
                base_stem=base_stem,
                citation_title=citation_title,
                book_code=book_code,
                ascii_alias=alias,
                source_pdf=source_pdf,
            )
        )

    return file_plan, base_plans


def write_plan(file_plan: List[Dict], base_plans: List[BasePlan]) -> None:
    payload = {
        "generated_at": datetime.now().isoformat(),
        "workspace_root": str(ROOT),
        "target_dir": str(MD_DIR),
        "change_order": [
            "1. source_title_registry.json 병합",
            "2. chunks_index.json 경로 갱신",
            "3. markdown 파일 rename 실행",
        ],
        "base_entries": [vars(entry) for entry in base_plans],
        "files": file_plan,
    }
    PLAN_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_registry(base_plans: List[BasePlan]) -> Dict:
    registry = load_existing_registry()
    registry["version"] = "1.0"
    registry["updated_at"] = datetime.now().strftime("%Y-%m-%d")
    notes = registry.get("notes", [])
    for note in [
        "match_stems should omit the trailing chunk suffix such as _p001-030.",
        "ascii_alias is the short ASCII markdown stem you plan to rename to.",
        "citation_title is the Korean source name that responses should cite.",
    ]:
        if note not in notes:
            notes.append(note)
    registry["notes"] = notes

    merged: Dict[Tuple[str, str], Dict] = {}
    for entry in registry.get("entries", []):
        key = (entry.get("book_code", ""), entry.get("citation_title", ""))
        merged[key] = entry

    for base in base_plans:
        key = (base.book_code, base.citation_title)
        existing = merged.get(
            key,
            {
                "match_stems": [],
                "book_code": base.book_code,
                "ascii_alias": base.ascii_alias,
                "citation_title": base.citation_title,
                "source_pdf": base.source_pdf,
            },
        )
        match_stems = set(existing.get("match_stems", []))
        match_stems.add(base.base_stem)
        match_stems.add(base.ascii_alias)
        existing["match_stems"] = sorted(match_stems)
        existing["book_code"] = base.book_code
        existing["ascii_alias"] = base.ascii_alias
        existing["citation_title"] = base.citation_title
        if base.source_pdf:
            existing["source_pdf"] = base.source_pdf
        merged[key] = existing

    registry["entries"] = sorted(merged.values(), key=lambda item: (item.get("book_code", ""), item.get("citation_title", "")))
    return registry


def update_chunks_index(file_plan: List[Dict], base_plans: List[BasePlan]) -> None:
    if not CHUNKS_INDEX_PATH.exists():
        return

    payload = json.loads(CHUNKS_INDEX_PATH.read_text(encoding="utf-8"))
    file_name_map = {item["old_name"]: item["new_name"] for item in file_plan}
    base_map = {item.base_stem: item for item in base_plans}

    for source in payload.get("sources", []):
        stem = Path(source.get("file", "")).stem
        if stem in base_map:
            source["source_title"] = base_map[stem].citation_title
            source["ascii_alias"] = base_map[stem].ascii_alias
        source["chunks"] = [file_name_map.get(name, name) for name in source.get("chunks", [])]

    for chunk in payload.get("chunks", []):
        old_file = chunk.get("file", "")
        new_file = file_name_map.get(old_file, old_file)
        chunk["file"] = new_file
        stem = strip_chunk_suffix(Path(new_file).stem)
        if stem in base_map:
            base = base_map[stem]
            chunk["source_title"] = base.citation_title
            chunk["ascii_alias"] = base.ascii_alias
        old_id = chunk.get("id", "")
        old_id_stem = strip_chunk_suffix(old_id)
        if old_id_stem in base_map:
            suffix = old_id[len(old_id_stem):]
            chunk["id"] = f"{base_map[old_id_stem].ascii_alias}{suffix}"

    CHUNKS_INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def execute_plan(file_plan: List[Dict]) -> Dict:
    collisions = []
    for item in file_plan:
        old_path = Path(item["path"])
        new_path = old_path.with_name(item["new_name"])
        if new_path.exists() and new_path != old_path:
            collisions.append(str(new_path))
    if collisions:
        raise RuntimeError(f"Rename collision detected: {collisions[:5]}")

    renamed = []
    for item in file_plan:
        old_path = Path(item["path"])
        new_path = old_path.with_name(item["new_name"])
        if old_path == new_path:
            continue
        old_path.rename(new_path)
        renamed.append({"old": str(old_path), "new": str(new_path)})

    return {"renamed_count": len(renamed), "renamed": renamed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Rename pdf_extracts markdown files to ASCII aliases")
    parser.add_argument("--execute", action="store_true", help="Apply registry/chunks_index updates and rename files")
    args = parser.parse_args()

    file_plan, base_plans = build_plan()
    write_plan(file_plan, base_plans)

    if not args.execute:
        print(f"[preview] files={len(file_plan)} bases={len(base_plans)}")
        print(f"[preview] plan={PLAN_PATH}")
        for item in file_plan[:20]:
            print(item["summary"])
        return

    registry = merge_registry(base_plans)
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    update_chunks_index(file_plan, base_plans)
    result = execute_plan(file_plan)

    log_payload = {
        "executed_at": datetime.now().isoformat(),
        "target_dir": str(MD_DIR),
        "plan_path": str(PLAN_PATH),
        "registry_path": str(REGISTRY_PATH),
        "chunks_index_path": str(CHUNKS_INDEX_PATH),
        **result,
    }
    LOG_PATH.write_text(json.dumps(log_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[done] renamed={result['renamed_count']}")
    print(f"[done] plan={PLAN_PATH}")
    print(f"[done] log={LOG_PATH}")


if __name__ == "__main__":
    main()
