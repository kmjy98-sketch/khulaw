#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Source registry helpers.

This registry lets extracted markdown filenames use short ASCII aliases while
citations continue to use the original Korean source title.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict


REGISTRY_RELATIVE_PATH = Path(".agent") / "state" / "source_title_registry.json"


def get_registry_path(root: Path) -> Path:
    return root / REGISTRY_RELATIVE_PATH


def strip_chunk_suffix(stem: str) -> str:
    stem = re.sub(r"_p\d{1,4}-\d{1,4}$", "", stem)
    stem = re.sub(r"_p\d{1,4}$", "", stem)
    stem = re.sub(r"_full$", "", stem)
    return stem


def strip_code_prefix(stem: str) -> str:
    match = re.match(r"(\d+-\d+)_(.+)$", stem)
    return match.group(2) if match else stem


def extract_book_code(text: str) -> str:
    match = re.search(r"(\d+-\d+)", text or "")
    return match.group(1) if match else ""


def normalize_key(text: str) -> str:
    return strip_chunk_suffix((text or "").strip()).casefold()


@lru_cache(maxsize=4)
def _load_registry_lookup(root_str: str) -> Dict[str, Dict]:
    root = Path(root_str)
    path = get_registry_path(root)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    lookup: Dict[str, Dict] = {}
    for entry in data.get("entries", []):
        keys = set()

        for value in entry.get("match_stems", []):
            if value:
                keys.add(normalize_key(value))

        ascii_alias = entry.get("ascii_alias", "")
        if ascii_alias:
            keys.add(normalize_key(ascii_alias))

        citation_title = entry.get("citation_title", "")
        if citation_title:
            keys.add(normalize_key(citation_title))

        source_pdf = entry.get("source_pdf", "")
        if source_pdf:
            keys.add(normalize_key(Path(source_pdf).stem))

        for key in keys:
            lookup[key] = entry

    return lookup


def resolve_source_entry(root: Path, stem_or_name: str) -> Dict:
    if not stem_or_name:
        return {}

    source_name = Path(stem_or_name).stem if Path(stem_or_name).suffix else stem_or_name
    return dict(_load_registry_lookup(str(root)).get(normalize_key(source_name), {}))


def resolve_source_metadata(
    root: Path,
    stem_or_name: str,
    fallback_book_code: str = "",
    fallback_title: str = "",
) -> Dict[str, str]:
    source_name = Path(stem_or_name).stem if Path(stem_or_name).suffix else stem_or_name
    base_stem = strip_chunk_suffix(source_name)
    entry = resolve_source_entry(root, base_stem)

    citation_title = entry.get("citation_title") or fallback_title or strip_code_prefix(base_stem)
    return {
        "book_code": entry.get("book_code") or fallback_book_code or extract_book_code(base_stem),
        "citation_title": citation_title,
        "source_title": citation_title,
        "source_pdf": entry.get("source_pdf", ""),
        "ascii_alias": entry.get("ascii_alias", ""),
    }
