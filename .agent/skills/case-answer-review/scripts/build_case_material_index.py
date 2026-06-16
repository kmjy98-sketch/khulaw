#!/usr/bin/env python3
"""민법 사례형 문제/해설/채점평/모답 파일을 묶어 인덱스를 생성한다."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(r"H:\내 드라이브")
STATE_DIR = ROOT / ".agent" / "state"
DEFAULT_INDEX = STATE_DIR / "case_material_index.json"
DEFAULT_LOG = STATE_DIR / "case_material_index_log.json"
SCAN_ROOTS = [
    ROOT / "1.민사",
    ROOT / "hwp pdf 변환",
    ROOT / "_hwp_모음" / "pdf_converted" / "hwp pdf 변환",
]
EXTRACT_ROOTS = [
    ROOT / ".agent" / "data" / "pdf_extracts",
    ROOT / ".agent" / "data" / "exam_extracts",
    ROOT / "1.민사" / "보관" / "윤동환_민법" / "교재",
    ROOT / "1.민사" / "보관" / "추출파일",
]


def normalize_file_token(value: str) -> str:
    token = re.sub(r"_p\d{3}-\d{3}$", "", value)
    token = re.sub(r"\(\d+\)$", "", token)
    token = re.sub(r"[\(\)\[\]{}]", "_", token)
    token = re.sub(r"[^0-9A-Za-z가-힣]+", "_", token)
    token = re.sub(r"_+", "_", token).strip("_")
    return token.lower()


def normalize_bundle_key(value: str) -> str:
    token = normalize_file_token(value)
    for marker in [
        "문제",
        "사례형",
        "사례",
        "해설",
        "채점평",
        "채점기준표",
        "답안_및_해설",
        "모답",
        "정답_및_해설",
    ]:
        token = token.replace(marker, "_")
    token = re.sub(r"_+", "_", token).strip("_")
    return token


def classify_case_file(name: str) -> str | None:
    if "민법" not in name:
        return None
    if "문제" in name and ("사례" in name or "사례형" in name):
        return "question"
    if "채점평" in name or "채점기준표" in name:
        return "grading"
    if "모답" in name:
        return "model_answer"
    if "해설" in name or "답안_및_해설" in name:
        return "explanation"
    return None


def infer_round(name: str) -> int | None:
    patterns = [
        r"모의\s*(\d+)회",
        r"모의(\d+)회",
        r"DT\s*(\d+)회",
        r"DT선택형(\d+)차",
        r"(\d+)차",
    ]
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            return int(match.group(1))
    return None


def build_extract_map() -> dict[str, list[str]]:
    extract_map: dict[str, list[str]] = defaultdict(list)
    for root in EXTRACT_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            extract_map[normalize_file_token(path.stem)].append(str(path))
    return dict(extract_map)


def match_extracts(file_stem: str, extract_map: dict[str, list[str]]) -> list[str]:
    key = normalize_file_token(file_stem)
    matches: list[str] = []
    for extract_key, paths in extract_map.items():
        if key == extract_key or key in extract_key or extract_key in key:
            matches.extend(paths)
    unique: list[str] = []
    seen = set()
    for path in matches:
        if path in seen:
            continue
        seen.add(path)
        unique.append(path)
    return unique[:6]


def main() -> None:
    parser = argparse.ArgumentParser(description="민법 사례형 자료 인덱스 생성")
    parser.add_argument("--index-output", default=str(DEFAULT_INDEX), help="인덱스 JSON 경로")
    parser.add_argument("--log-output", default=str(DEFAULT_LOG), help="진행로그 JSON 경로")
    args = parser.parse_args()

    extract_map = build_extract_map()
    bundles: dict[str, dict[str, Any]] = {}
    log: dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scan_roots": [str(root) for root in SCAN_ROOTS],
        "processed_files": [],
    }

    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.pdf"):
            kind = classify_case_file(path.name)
            if not kind:
                continue

            bundle_key = normalize_bundle_key(path.stem)
            bundle = bundles.setdefault(
                bundle_key,
                {
                    "bundle_key": bundle_key,
                    "subject": "민법",
                    "round_hint": infer_round(path.stem),
                    "files": {
                        "question": [],
                        "explanation": [],
                        "grading": [],
                        "model_answer": [],
                    },
                },
            )

            extract_matches = match_extracts(path.stem, extract_map)
            record = {
                "name": path.name,
                "path": str(path),
                "kind": kind,
                "extract_md": extract_matches,
            }
            bundle["files"][kind].append(record)
            log["processed_files"].append(
                {
                    "path": str(path),
                    "bundle_key": bundle_key,
                    "kind": kind,
                    "extract_count": len(extract_matches),
                    "status": "indexed",
                }
            )

    index_payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bundle_count": len(bundles),
        "bundles": sorted(bundles.values(), key=lambda item: (item.get("round_hint") or 999, item["bundle_key"])),
    }

    index_path = Path(args.index_output)
    log_path = Path(args.log_output)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"사례형 번들 수: {index_payload['bundle_count']}")
    print(f"인덱스 저장됨: {index_path}")
    print(f"로그 저장됨: {log_path}")


if __name__ == "__main__":
    main()
