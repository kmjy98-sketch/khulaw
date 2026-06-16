#!/usr/bin/env python3
"""Parse local legal template markdown into structured data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def parse_templates(path: str | Path) -> dict:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    sections: dict[str, dict] = {}
    current_section: str | None = None
    current_template: str | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("# "):
            continue

        if line.startswith("## "):
            current_section = normalize_key(line[3:])
            sections[current_section] = {"fields": {}, "templates": {}}
            current_template = None
            continue

        if line.startswith("### ") and current_section:
            current_template = normalize_key(line[4:])
            sections[current_section]["templates"][current_template] = {}
            continue

        if not line.startswith("- ") or not current_section:
            continue

        key, _, value = line[2:].partition(":")
        key = normalize_key(key)
        value = value.strip()

        if current_template:
            sections[current_section]["templates"][current_template][key] = value
        else:
            sections[current_section]["fields"][key] = value

    return {
        "source": str(path),
        "sections": sections,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse legal template markdown")
    parser.add_argument("template_path", help="Template markdown path")
    args = parser.parse_args()

    data = parse_templates(args.template_path)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
