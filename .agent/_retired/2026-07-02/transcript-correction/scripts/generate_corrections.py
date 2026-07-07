#!/usr/bin/env python3
"""
Generate heuristic corrected transcript parts for uncorrected transcript folders.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from correction_state import COR_SUFFIX, derive_state, list_raw_parts
from duplicate_transcripts import build_duplicate_index

ROOT = Path(__file__).resolve().parents[4]
LOG_PATH = ROOT / ".agent" / "state" / "transcription_log.json"
REPORT_PATH = ROOT / ".agent" / "state" / f"correction_run_{date.today().isoformat()}.txt"

SAFE_REPLACEMENTS: list[tuple[str, str]] = [
    ("\ub300\ud45c\uae30\uad00\uc758 \uace0\ub09c\uc758 \uc77c\ud0c8", "\ub300\ud45c\uae30\uad00\uc758 \uad8c\ud55c\uc758 \uc77c\ud0c8"),
    ("\uae08\uc800\uc18c\ube44\ub300\ucc28\uae30\uc57d", "\uae08\uc804\uc18c\ube44\ub300\ucc28\uacc4\uc57d"),
    ("\uae08\uc800\uc18c\ube44\ub300\ucc28 \uacc4\uc57d", "\uae08\uc804\uc18c\ube44\ub300\ucc28\uacc4\uc57d"),
    ("\uae08\uc870\uc18c\ube44 \ub300\uc0c1 \uacc4\uc57d", "\uae08\uc804\uc18c\ube44\ub300\ucc28\uacc4\uc57d"),
    ("\uae08\uc870\uc18c\ube44 \ub300\uc0c1", "\uae08\uc804\uc18c\ube44\ub300\ucc28"),
    ("\uae08\uc804 \uc18c\ube44\ub300\ucc28 \uacc4\uc57d", "\uae08\uc804\uc18c\ube44\ub300\ucc28\uacc4\uc57d"),
    ("\uc601\uc720\ud558\ub294", "\uc601\uc704\ud558\ub294"),
    ("\uc6c0\uc9c1\ud574\uc57c", "\uc6c0\uc9c1\uc5ec\uc57c"),
    ("\uad50\uc81c", "\uad50\uc7ac"),
    ("\uae30\ubcf8\uad50\uc81c", "\uae30\ubcf8\uad50\uc7ac"),
    ("\uad00\ub9ac \uc758\ubb34\uc758 \ubc1c\uc0dd \uc6d0\uc778", "\uad8c\ub9ac \uc758\ubb34\uc758 \ubc1c\uc0dd \uc6d0\uc778"),
    ("\uc870\ud68c\uac00 \uae4a\uc5b4\uc9c4\ub2e4", "\uc870\uc608\uac00 \uae4a\uc5b4\uc9c4\ub2e4"),
    ("\uccad\ub7b5", "\uccad\uc57d"),
    ("\uc2b9\ub7b5", "\uc2b9\ub099"),
    ("\uc704\ubc95\uc804", "\ubbfc\ubc95\uc804"),
    ("\uc18d\uc785\uc218", "\uc18d\uc784\uc218"),
    ("\ub178\uc2e4", "\uc624\uc2e0"),
    ("\uc81c\ud55c\uc131\ud615\uc790", "\uc81c\ud55c\ub2a5\ub825\uc790"),
    ("\ub2a5\ub825\uc790\ub85c \ubb36\uac8c", "\ub2a5\ub825\uc790\ub85c \ubbff\uac8c"),
    ("\ub2a5\ub825\uc790\uc778 \uac83\ucc98\ub7fc \ubb36\uac8c", "\ub2a5\ub825\uc790\uc778 \uac83\ucc98\ub7fc \ubbff\uac8c"),
    ("\ubc95\uc815\ub0b4\ub9bc", "\ubc95\uc815\ub300\ub9ac\uc778"),
    ("\ubc95\uc815\ub300\ub9ac\uc778\uc758 \ub3d9\uc758\uac00 \uc788\ub294 \uac83\uc744 \ubb34\uc2dc\ud55c \uacbd\uc6b0", "\ubc95\uc815\ub300\ub9ac\uc778\uc758 \ub3d9\uc758\uac00 \uc788\ub294 \uac83\uc73c\ub85c \ubbff\uac8c \ud55c \uacbd\uc6b0"),
    ("\ubc95\uc815\ub300\ub9ac\uc778\uc758 \ub3d9\uc758\uac00 \uc788\ub294 \uac83\uc744 \ubb34\uc2dc\ud55c\ub2e4", "\ubc95\uc815\ub300\ub9ac\uc778\uc758 \ub3d9\uc758\uac00 \uc788\ub294 \uac83\uc73c\ub85c \ubbff\uac8c \ud55c\ub2e4"),
    ("\uadf8 \ud589\uc704\ub97c \ucd9c\ubc1c\ud560 \uc218 \uc5c6\ub2e4", "\uadf8 \ud589\uc704\ub97c \ucde8\uc18c\ud560 \uc218 \uc5c6\ub2e4"),
    ("\ubc95\ub960\uc744 \uc704\ubc18\ud588\uc744 \uac70", "\ubc95\ub960\ud589\uc704\ub97c \ud588\uc744 \uac70"),
    ("\uc77c\ud654\uac00 \uc5c6\ub2e4", "\ucde8\uc18c\ud560 \uc218 \uc5c6\ub2e4"),
    ("\uc774\uc655\ub3c4", "2\ud56d\ub3c4"),
    ("\uc774\uc655\uc740", "2\ud56d\uc740"),
    ("\uc774\ub791\uc740", "2\ud56d\uc740"),
    ("\ub2a6\uac8c \ud55c \uacbd\uc6b0", "\ubbff\uac8c \ud55c \uacbd\uc6b0"),
    ("\uae08\uc0c1\ubb38\uc81c\ub098", "\ubbf8\uc131\ub144\uc790\ub098"),
    ("\ube44\ub9dd", "\uae30\ub9dd"),
    ("\ud53c\uc131\ub144\uc790\uc77c \uc218\ub3c4 \uc788\uace0 \ud53c\ud55c\uc815\ud6c4\uacac\uc778\uc790\uc77c \uc218\ub3c4", "\ud53c\uc131\ub144\ud6c4\uacac\uc778\uc77c \uc218\ub3c4 \uc788\uace0 \ud53c\ud55c\uc815\ud6c4\uacac\uc778\uc77c \uc218\ub3c4"),
    ("\ud53c\ud55c\uc815\ud6c4\uacac\uc778\uc790", "\ud53c\ud55c\uc815\ud6c4\uacac\uc778"),
    ("\uc18d\uc784\uc218 \ub123\uc5b4\uac00\uc9c0\uace0", "\uc18d\uc784\uc218 \uc368\uac00\uc9c0\uace0"),
    ("\ud53c\uc131\ub144\ud6c4\uacac\uc778\uc774\ub294", "\ud53c\uc131\ub144\ud6c4\uacac\uc778\uc740"),
    ("\uac70\ub871\uc774", "\uac78\ub9bc\uc774"),
    ("\uc704\ubc95\ud589\uc704", "\ubd88\ubc95\ud589\uc704"),
    ("\uc0ac\uc0dd\uc0b0 \uccad\uad6c", "\uc190\ud574\ubc30\uc0c1 \uccad\uad6c"),
    ("\uc0ac\uae30\uc5d0 \uc758\ud55c \uc758\uc0ac\ud45c\uc2dc", "\uc0ac\uae30\uc5d0 \uc758\ud55c \uc758\uc0ac\ud45c\uc2dc"),
    ("\uc704\ubc95\ud589\uc704\uc758 \uc758\uc0ac\ud45c\uc2dc", "\uc0ac\uae30\uc5d0 \uc758\ud55c \uc758\uc0ac\ud45c\uc2dc"),
    ("\ubd88\ubc95\ud589\uc704\uc758 \uc758\uc0ac\ud45c\uc2dc\ub85c \ub9e4\ub9e4 \uacc4\uc57d\uc744 \uc758\ub9ac.", "\uc0ac\uae30\uc5d0 \uc758\ud55c \uc758\uc0ac\ud45c\uc2dc\ub85c \ub9e4\ub9e4\uacc4\uc57d\uc744 \ucde8\uc18c\ud560 \uc218 \uc788\uc5b4\uc694."),
    ("\ubd88\ubc95\ud589\uc704\uc5d0\uac8c \uc190\ud574\ubc30\uc0c1 \uccad\uad6c", "\ubd88\ubc95\ud589\uc704\uc5d0 \uc758\ud55c \uc190\ud574\ubc30\uc0c1 \uccad\uad6c"),
    ("\ubd88\ubc95\ud589\uc704\uc5d0\uac8c \uc190\ud574\uac00 \uc0dd\uacbc\ub2e4\ub294", "\ubd88\ubc95\ud589\uc704\uc5d0 \uc758\ud55c \uc190\ud574\uac00 \uc0dd\uacbc\ub2e4\ub294"),
    ("\uc190\ud574\ubc30\uc0c1\uc73c\ub85c \uc77c\uc815\ud55c\ub2e4\uace0", "\uc190\ud574\ubc30\uc0c1\uc73c\ub85c \uc778\uc815\ud55c\ub2e4\uace0"),
    ("\uc131\uae09\ud574\uc11c \ubb34\ud6a8\uac00 \ub3fc", "\uc18c\uae09\ud574\uc11c \ubb34\ud6a8\uac00 \ub3fc"),
    ("\uc720\ud6a8 \ud30c\uc545", "\uc720\ucd94 \ud30c\uc545"),
    ("\ubcf8 \ud589\uc704\ub97c \ucd95\ud558\ud560 \uc218 \uc5c6\ub294 \uac83\uc73c\ub85c \ud558\uc600\ub2e4", "\ubcf8 \ud589\uc704\ub97c \ucde8\uc18c\ud560 \uc218 \uc5c6\ub294 \uac83\uc73c\ub85c \ud558\uc600\ub2e4"),
    ("\ubc95\uc815\ub300\uc704", "\ubc95\uc815\ub300\ub9ac\uc778"),
    ("\uc778\uae30\ud55c \uacbd\uc6b0", "\ubbff\uac8c \ud55c \uacbd\uc6b0"),
    ("\ud53c\uc131\ub144\ud6c4\ubcc0\uc778", "\ud53c\uc131\ub144\ud6c4\uacac\uc778"),
]

REGEX_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile("(?<!\uC81C)(\\d+)\uC870"), "\uC81C\\1\uC870"),
    (re.compile("(?<!\uC81C)(\\d+)\uD56D"), "\uC81C\\1\uD56D"),
    (re.compile("(?<!\uC81C)(\\d+)\uD638"), "\uC81C\\1\uD638"),
    (re.compile("\uD53C\uC131\uB144\uD6C4\uACAC(?!\uC778)"), "\uD53C\uC131\uB144\uD6C4\uACAC\uC778"),
    (re.compile("\uD53C\uD55C\uC815\uD6C4\uACAC(?!\uC778)"), "\uD53C\uD55C\uC815\uD6C4\uACAC\uC778"),
    (re.compile("\uBC95\uC815\uB300\uB9AC\uC778\uC5D0 \uB3D9\uC758"), "\uBC95\uC815\uB300\uB9AC\uC778\uC758 \uB3D9\uC758"),
    (re.compile("\uBC95\uB960 \uD589\uC704"), "\uBC95\uB960\uD589\uC704"),
    (re.compile("\uBC95\uC815 \uB300\uB9AC\uC778"), "\uBC95\uC815\uB300\uB9AC\uC778"),
    (re.compile("\uC7AC\uC0B0 \uAD00\uB9AC\uC778"), "\uC7AC\uC0B0\uAD00\uB9AC\uC778"),
    (re.compile("\uC2E4\uC885 \uC120\uACE0"), "\uC2E4\uC885\uC120\uACE0"),
    (re.compile("\uAC15\uC81C \uACBD\uB9E4"), "\uAC15\uC81C\uACBD\uB9E4"),
    (re.compile("\uC784\uC758 \uACBD\uB9E4"), "\uC784\uC758\uACBD\uB9E4"),
    (re.compile("(\uB9E4\uAC01\ud5c8\uAC00) \uACB0\uc815"), "\\1\uACB0\uC815"),
    (re.compile("(\\d+)\uCC9C\uB9CC\uC6D0"), "\\1\uCC9C\uB9CC \uC6D0"),
]

TIMESTAMP_RE = re.compile(r"^(\[\d{2}:\d{2}:\d{2}\]\s*)(.*)$")


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_log() -> dict:
    with open(LOG_PATH, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def save_log(data: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=4)


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("decode", b"", 0, 1, f"failed to decode: {path}")


def parse_seconds(line: str) -> int | None:
    match = TIMESTAMP_RE.match(line)
    if not match:
        return None
    hh, mm, ss = match.group(1)[1:9].split(":")
    return int(hh) * 3600 + int(mm) * 60 + int(ss)


def correct_body(text: str) -> str:
    for old, new in SAFE_REPLACEMENTS:
        text = text.replace(old, new)
    for pattern, replacement in REGEX_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    for old, new in SAFE_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def correct_line(line: str) -> str:
    match = TIMESTAMP_RE.match(line)
    if not match:
        return correct_body(line)
    prefix, body = match.groups()
    return prefix + correct_body(body)


def dedupe_lines(lines: list[str]) -> list[str]:
    result: list[str] = []
    prev_body = None
    prev_sec = None
    for line in lines:
        match = TIMESTAMP_RE.match(line)
        if not match:
            result.append(line)
            prev_body = None
            prev_sec = None
            continue

        body = match.group(2).strip()
        sec = parse_seconds(line)
        if result and body and prev_body == body and sec is not None and prev_sec is not None and sec - prev_sec <= 2:
            continue

        result.append(line)
        prev_body = body
        prev_sec = sec
    return result


def collect_targets(log_data: dict) -> tuple[list[dict], list[dict]]:
    targets: list[dict] = []
    missing: list[dict] = []
    duplicate_index = build_duplicate_index(log_data)
    seen = set()
    for transcript_path, info in sorted(log_data.items()):
        split_dir = Path(info.get("split_dir") or "")
        duplicate_info = duplicate_index.get(transcript_path)
        info["duplicate_of"] = duplicate_info["duplicate_of"] if duplicate_info else ""
        info["duplicate_reason"] = duplicate_info["duplicate_reason"] if duplicate_info else ""
        state_info = derive_state(info, split_dir, stale_reason="split_dir missing")
        if state_info["correction_state"] in {"reviewed", "duplicate"}:
            continue
        key = str(split_dir)
        if key in seen:
            continue
        seen.add(key)

        if not split_dir.exists():
            info["corrected"] = False
            info["correction_state"] = "stale"
            info["stale_reason"] = "split_dir missing"
            missing.append(
                {
                    "transcript_path": transcript_path,
                    "split_dir": str(split_dir),
                    "correction_state": "stale",
                    "reason": "split_dir missing",
                }
            )
            continue

        part_files = list_raw_parts(split_dir)
        if not part_files:
            missing.append(
                {
                    "transcript_path": transcript_path,
                    "split_dir": str(split_dir),
                    "correction_state": state_info["correction_state"],
                    "reason": "part files missing",
                }
            )
            continue

        targets.append(
            {
                "transcript_path": transcript_path,
                "split_dir": split_dir,
                "part_files": part_files,
            }
        )
    return targets, missing


def corrected_path(raw_path: Path) -> Path:
    return raw_path.with_name(raw_path.stem + COR_SUFFIX)


def generate_for_part(raw_path: Path, force: bool) -> tuple[str, Path]:
    target = corrected_path(raw_path)
    if target.exists() and not force:
        return "skip_existing", target

    text = read_text(raw_path)
    corrected_lines = [correct_line(line) for line in text.splitlines()]
    corrected_lines = dedupe_lines(corrected_lines)
    output = "\n".join(corrected_lines)
    if text.endswith("\n"):
        output += "\n"

    target.write_text(output, encoding="utf-8")
    return "created", target


def write_report(rows: list[str]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> int:
    configure_stdio()

    force = "--force" in sys.argv[1:]
    log_data = load_log()
    targets, missing = collect_targets(log_data)
    save_log(log_data)

    report_rows: list[str] = []
    created = 0
    skipped = 0

    report_rows.append(f"TARGET_DIRS={len(targets)}")
    report_rows.append(f"MISSING_DIRS={len(missing)}")

    for row in missing:
        report_rows.append("---")
        report_rows.append(f"MISSING transcript_path: {row['transcript_path']}")
        report_rows.append(f"MISSING split_dir: {row['split_dir']}")
        report_rows.append(f"MISSING state: {row['correction_state']}")
        report_rows.append(f"MISSING reason: {row['reason']}")

    for target in targets:
        report_rows.append("---")
        report_rows.append(f"DIR transcript_path: {target['transcript_path']}")
        report_rows.append(f"DIR split_dir: {target['split_dir']}")
        for part_file in target["part_files"]:
            status, path = generate_for_part(part_file, force=force)
            if status == "created":
                created += 1
            else:
                skipped += 1
            report_rows.append(f"{status.upper()} {path}")

    report_rows.append("---")
    report_rows.append(f"CREATED={created}")
    report_rows.append(f"SKIPPED_EXISTING={skipped}")
    write_report(report_rows)

    print(f"TARGET_DIRS={len(targets)}")
    print(f"MISSING_DIRS={len(missing)}")
    print(f"CREATED={created}")
    print(f"SKIPPED_EXISTING={skipped}")
    print(f"REPORT={REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
