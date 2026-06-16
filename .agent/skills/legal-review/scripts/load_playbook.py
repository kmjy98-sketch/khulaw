#!/usr/bin/env python3
"""법무 플레이북 마크다운 파서."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def parse_list(value: str) -> list[str]:
    parts = [item.strip() for item in value.split(",")]
    return [item for item in parts if item]


def parse_playbook(path: str | Path) -> dict:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    metadata: dict[str, str] = {}
    clauses: list[dict] = []
    current: dict | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("## "):
            current = None
            continue

        if line.startswith("### "):
            if current:
                clauses.append(current)
            current = {
                "clause": line[4:].strip(),
                "keywords": [],
                "favorable_signals": [],
                "standard_position": "",
                "acceptable_range": "",
                "fallback_position": "",
                "redline_suggestion": "",
                "business_impact": "",
                "negotiation_priority": "",
                "escalation_triggers": [],
                "notes": [],
            }
            continue

        if line.startswith("- ") and current is None:
            key, _, value = line[2:].partition(":")
            if value:
                metadata[key.strip().lower().replace(" ", "_")] = value.strip()
            continue

        if not current or not line.startswith("- "):
            continue

        key, _, value = line[2:].partition(":")
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()

        if key == "keywords":
            current["keywords"].extend(parse_list(value))
        elif key == "favorable_signal":
            current["favorable_signals"].append(value)
        elif key == "favorable_signals":
            current["favorable_signals"].extend(parse_list(value))
        elif key == "standard_position":
            current["standard_position"] = value
        elif key == "acceptable_range":
            current["acceptable_range"] = value
        elif key == "fallback_position":
            current["fallback_position"] = value
        elif key == "redline_suggestion":
            current["redline_suggestion"] = value
        elif key == "business_impact":
            current["business_impact"] = value
        elif key == "negotiation_priority":
            current["negotiation_priority"] = value
        elif key == "escalation_trigger":
            current["escalation_triggers"].append(value)
        else:
            current["notes"].append(line[2:].strip())

    if current:
        clauses.append(current)

    return {
        "source": str(path),
        "metadata": metadata,
        "clauses": clauses,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="법무 플레이북 마크다운 파서")
    parser.add_argument("playbook_path", help="플레이북 마크다운 경로")
    args = parser.parse_args()

    data = parse_playbook(args.playbook_path)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
