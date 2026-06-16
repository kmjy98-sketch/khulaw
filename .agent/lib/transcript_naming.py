#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transcript ASCII alias helpers.

This registry keeps transcript and correction filenames short and ASCII-only
while preserving the Korean lecture/course names in folder structure and logs.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Tuple


RULES_RELATIVE_PATH = Path(".agent") / "state" / "transcript_alias_rules.json"

DEFAULT_TEMPLATES = {
    "session_dir": "{stem}",
    "transcript": "{stem}_transcript.txt",
    "part": "{stem}_part{part:02d}.md",
    "part_corr": "{stem}_part{part:02d}_corr.md",
    "corr": "{stem}_corr.md",
    "corr_merged": "{stem}_corr_merged.md",
}
KNOWN_FILE_SUFFIXES = {".md", ".txt"}


def get_rules_path(root: Path) -> Path:
    return root / RULES_RELATIVE_PATH


def normalize_match_text(text: str) -> str:
    value = (text or "").strip().replace(" ", "_")
    value = re.sub(r"_+", "_", value)
    return value.strip("_").casefold()


def is_ascii_text(text: str) -> bool:
    try:
        (text or "").encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def canonicalize_session_token(token: str) -> str:
    value = (token or "").strip().replace(" ", "")
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        return ""

    lower_value = value.casefold()
    if re.fullmatch(r"lec\d+(?:to\d+)?", lower_value):
        return lower_value

    match = re.fullmatch(r"(\d+)~(\d+)강", value)
    if match:
        return f"lec{int(match.group(1))}to{int(match.group(2))}"

    match = re.fullmatch(r"(\d+)강", value)
    if match:
        return f"lec{int(match.group(1))}"

    return value.replace("~", "to")


def build_canonical_stem(ascii_alias: str, session_token: str) -> str:
    if not ascii_alias:
        return session_token
    return f"{ascii_alias}_{session_token}" if session_token else ascii_alias


def strip_known_file_suffix(text: str) -> str:
    path = Path(text)
    if path.suffix.lower() in KNOWN_FILE_SUFFIXES:
        return path.stem
    return text


def analyze_transcript_name(name: str, is_dir: bool = False) -> Dict:
    path = Path(name)
    extension = "" if is_dir else path.suffix.lower()
    stem = path.name if is_dir else path.stem

    patterns = [
        ("corr_merged", re.compile(r"^(?P<base>.+?)_corr_merged$", re.IGNORECASE)),
        ("corr_merged", re.compile(r"^(?P<base>.+?)_교정본_통합$")),
        ("part_corr", re.compile(r"^(?P<base>.+?)_part(?P<part>\d{1,2})_corr$", re.IGNORECASE)),
        ("part_corr", re.compile(r"^(?P<base>.+?)_part(?P<part>\d{1,2})_교정$")),
        ("part", re.compile(r"^(?P<base>.+?)_part(?P<part>\d{1,2})$", re.IGNORECASE)),
        ("corr", re.compile(r"^(?P<base>.+?)_corr$", re.IGNORECASE)),
        ("corr", re.compile(r"^(?P<base>.+?)_교정$")),
        ("transcript", re.compile(r"^(?P<base>.+?)_transcript$", re.IGNORECASE)),
    ]

    for kind, pattern in patterns:
        match = pattern.match(stem)
        if match:
            part = match.groupdict().get("part")
            return {
                "kind": kind,
                "base_stem": match.group("base"),
                "part": int(part) if part else None,
                "extension": extension,
            }

    return {
        "kind": "plain",
        "base_stem": stem,
        "part": None,
        "extension": extension,
    }


@lru_cache(maxsize=4)
def _load_rules(root_str: str) -> Dict:
    root = Path(root_str)
    path = get_rules_path(root)
    if not path.exists():
        return {"templates": dict(DEFAULT_TEMPLATES), "aliases": [], "_aliases": []}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"templates": dict(DEFAULT_TEMPLATES), "aliases": [], "_aliases": []}

    templates = dict(DEFAULT_TEMPLATES)
    templates.update(data.get("templates", {}))

    prepared_aliases = []
    for raw_entry in data.get("aliases", []):
        entry = dict(raw_entry)
        prefixes = set(entry.get("match_prefixes", []))
        ascii_alias = entry.get("ascii_alias", "")
        if ascii_alias:
            prefixes.add(ascii_alias)

        norm_prefixes = sorted(
            {normalize_match_text(prefix) for prefix in prefixes if prefix},
            key=len,
            reverse=True,
        )
        entry["_norm_prefixes"] = norm_prefixes
        entry["_priority"] = max((len(prefix) for prefix in norm_prefixes), default=0)
        prepared_aliases.append(entry)

    prepared_aliases.sort(key=lambda item: item["_priority"], reverse=True)

    return {
        "version": data.get("version", ""),
        "templates": templates,
        "aliases": data.get("aliases", []),
        "_aliases": prepared_aliases,
    }


def load_rules(root: Path) -> Dict:
    loaded = _load_rules(str(root))
    return {
        "version": loaded.get("version", ""),
        "templates": dict(loaded.get("templates", {})),
        "aliases": [dict(entry) for entry in loaded.get("aliases", [])],
    }


def resolve_alias_entry(root: Path, stem_or_name: str) -> Tuple[Dict, str]:
    source_name = strip_known_file_suffix(stem_or_name)
    normalized = normalize_match_text(source_name)
    if not normalized:
        return {}, ""

    for entry in _load_rules(str(root)).get("_aliases", []):
        for prefix in entry.get("_norm_prefixes", []):
            if normalized == prefix:
                return dict(entry), ""
            if normalized.startswith(prefix + "_"):
                session = normalized[len(prefix) + 1 :]
                return dict(entry), canonicalize_session_token(session)

    return {}, ""


def build_name(root: Path, canonical_stem: str, kind: str, part: int | None, extension: str) -> str:
    templates = _load_rules(str(root)).get("templates", {}) or DEFAULT_TEMPLATES

    if kind == "transcript":
        return templates["transcript"].format(stem=canonical_stem)
    if kind == "part":
        return templates["part"].format(stem=canonical_stem, part=int(part or 0))
    if kind == "part_corr":
        return templates["part_corr"].format(stem=canonical_stem, part=int(part or 0))
    if kind == "corr":
        return templates["corr"].format(stem=canonical_stem)
    if kind == "corr_merged":
        return templates["corr_merged"].format(stem=canonical_stem)
    if extension:
        return f"{canonical_stem}{extension}"
    return templates.get("session_dir", "{stem}").format(stem=canonical_stem)


def canonicalize_transcript_name(
    root: Path,
    name: str,
    *,
    parent_session_stem: str | None = None,
    is_dir: bool = False,
) -> Dict:
    parsed = analyze_transcript_name(name, is_dir=is_dir)
    entry: Dict = {}

    if parent_session_stem:
        canonical_stem = parent_session_stem
    else:
        entry, session_token = resolve_alias_entry(root, parsed["base_stem"])
        if entry:
            canonical_stem = build_canonical_stem(entry.get("ascii_alias", ""), session_token)
        elif is_ascii_text(parsed["base_stem"]):
            canonical_stem = parsed["base_stem"]
        else:
            return {
                "matched": False,
                "changed": False,
                "canonical_name": name,
                "canonical_stem": parsed["base_stem"],
                "session_token": "",
                "entry": {},
                "kind": parsed["kind"],
                "part": parsed["part"],
                "extension": parsed["extension"],
            }

    canonical_name = build_name(
        root,
        canonical_stem,
        parsed["kind"],
        parsed["part"],
        parsed["extension"],
    )

    session_token = ""
    alias_prefix = entry.get("ascii_alias") if entry else ""
    if alias_prefix and canonical_stem.startswith(alias_prefix):
        suffix = canonical_stem[len(alias_prefix) :].lstrip("_")
        session_token = suffix
    elif parent_session_stem and "_" in canonical_stem:
        session_token = canonical_stem.split("_", 1)[1]

    return {
        "matched": bool(entry) or bool(parent_session_stem),
        "changed": canonical_name != name,
        "canonical_name": canonical_name,
        "canonical_stem": canonical_stem,
        "session_token": session_token,
        "entry": entry,
        "kind": parsed["kind"],
        "part": parsed["part"],
        "extension": parsed["extension"],
    }
