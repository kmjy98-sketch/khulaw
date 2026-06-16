#!/usr/bin/env python3
"""
Generic transcript splitter.
"""

import argparse
import math
import re
from pathlib import Path


def split_front_matter(content: str) -> tuple[str, str]:
    if not content.startswith("---\n"):
        return "", content

    end = content.find("\n---\n", 4)
    if end == -1:
        return "", content

    return content[: end + 5], content[end + 5 :]


def pick_cut_index(lines: list[str], start: int, target: int, remaining_parts: int) -> int:
    min_end = min(len(lines), start + max(1, target))
    max_end = len(lines) - max(remaining_parts - 1, 0)
    max_end = max(min_end, max_end)

    header_pattern = re.compile(r"^#{1,3}\s")
    blank_indexes = []
    header_indexes = []

    for index in range(min_end, min(len(lines), max_end)):
        line = lines[index]
        if header_pattern.match(line):
            header_indexes.append(index)
        if line.strip() == "":
            blank_indexes.append(index + 1)

    if header_indexes:
        return header_indexes[0]
    if blank_indexes:
        return blank_indexes[0]
    return min(len(lines), max(start + 1, min_end))


def split_lines(lines: list[str], parts: int) -> list[list[str]]:
    if not lines:
        return []

    chunks = []
    start = 0

    for part_index in range(parts):
        remaining_parts = parts - part_index
        remaining_lines = len(lines) - start
        if remaining_lines <= 0:
            break
        if remaining_parts == 1:
            end = len(lines)
        else:
            dynamic_target = max(1, math.ceil(remaining_lines / remaining_parts))
            end = pick_cut_index(lines, start, dynamic_target, remaining_parts)
        chunks.append(lines[start:end])
        start = end

    if start < len(lines):
        if chunks:
            chunks[-1].extend(lines[start:])
        else:
            chunks.append(lines[start:])

    return [chunk for chunk in chunks if chunk]


def write_chunks(source_file: Path, output_dir: Path, header: str, chunks: list[list[str]], dry_run: bool) -> None:
    stem = source_file.stem.replace("_transcript", "")

    for index, chunk in enumerate(chunks, start=1):
        target = output_dir / f"{stem}_part{index:02d}.md"
        char_count = sum(len(line) for line in chunk)
        if dry_run:
            print(f"[DRY-RUN] {target} ({char_count} chars)")
            continue
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            if header:
                handle.write(header)
                if not header.endswith("\n\n"):
                    handle.write("\n")
            handle.writelines(chunk)
        print(f"Created: {target.name} ({char_count} chars)")


def main() -> int:
    parser = argparse.ArgumentParser(description="전사문 분할")
    parser.add_argument("file", help="분할할 전사문 파일")
    parser.add_argument("--parts", "-p", type=int, default=10, help="분할 개수")
    parser.add_argument("--output", "-o", help="출력 폴더")
    parser.add_argument("--dry-run", action="store_true", help="파일 생성 없이 계획만 출력")
    args = parser.parse_args()

    source_file = Path(args.file)
    if not source_file.exists():
        print(f"Error: Source file not found: {source_file}")
        return 1
    if args.parts < 1:
        print("Error: --parts must be >= 1")
        return 1

    output_dir = Path(args.output) if args.output else source_file.parent
    content = source_file.read_text(encoding="utf-8")
    header, body = split_front_matter(content)
    lines = body.splitlines(keepends=True)
    chunks = split_lines(lines, args.parts)
    write_chunks(source_file, output_dir, header, chunks, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
