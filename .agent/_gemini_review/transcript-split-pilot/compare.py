#!/usr/bin/env python3
"""
Compare Claude (split_transcript.py) vs Gemini Flash output.
Run from the pilot directory.
"""

import hashlib
import re
import statistics
from pathlib import Path

PILOT = Path(__file__).parent
SOURCE = PILOT / "source" / "civ_song_basic_3-2.2_transcript.md"
CLAUDE_DIR = PILOT / "claude"
GEMINI_RAW = PILOT / "gemini_output_v3.md"
GEMINI_DIR = PILOT / "gemini"


def split_gemini_output() -> list[Path]:
    raw = GEMINI_RAW.read_text(encoding="utf-8")
    # Strip the marker we appended
    raw = raw.replace("==END_OF_TRANSCRIPT==", "")

    # Find every "## Part N" header by line-walking (handles glued prefix)
    lines = raw.splitlines(keepends=True)
    headers = [(i, ln) for i, ln in enumerate(lines) if re.search(r"## Part \d+", ln)]

    GEMINI_DIR.mkdir(exist_ok=True)
    # Clear previous files
    for old in GEMINI_DIR.glob("*.md"):
        old.unlink()

    files = []
    for n, (line_idx, _hdr_line) in enumerate(headers):
        next_idx = headers[n + 1][0] if n + 1 < len(headers) else len(lines)
        # body = lines after the header up to next header
        body_lines = lines[line_idx + 1 : next_idx]
        body = "".join(body_lines)
        out = GEMINI_DIR / f"civ_song_basic_3-2.2_gemini_part{n+1:02d}.md"
        out.write_text(body, encoding="utf-8")
        files.append(out)
    return files


def file_size(p: Path) -> int:
    return p.stat().st_size


def char_count(p: Path) -> int:
    return len(p.read_text(encoding="utf-8"))


def count_timestamps(text: str) -> int:
    return len(re.findall(r"\[\d{2}:\d{2}:\d{2}\]", text))


def concat(files: list[Path]) -> str:
    return "".join(p.read_text(encoding="utf-8") for p in sorted(files))


def normalize(text: str) -> str:
    """Remove headers + whitespace differences for content-only diff."""
    # remove '## Part N' headers
    text = re.sub(r"^## Part \d+\s*\n", "", text, flags=re.MULTILINE)
    # remove leading/trailing whitespace per line
    return "".join(line.strip() + "\n" for line in text.splitlines() if line.strip())


def main() -> None:
    print("=== Source ===")
    src_text = SOURCE.read_text(encoding="utf-8")
    src_size = SOURCE.stat().st_size
    src_chars = len(src_text)
    src_ts = count_timestamps(src_text)
    print(f"size:        {src_size} bytes")
    print(f"chars:       {src_chars}")
    print(f"timestamps:  {src_ts}")
    print(f"sha256:      {hashlib.sha256(src_text.encode()).hexdigest()[:16]}")
    print()

    # --- Claude
    claude_files = sorted(CLAUDE_DIR.glob("*part*.md"))
    print(f"=== Claude ({len(claude_files)} parts) ===")
    sizes = [file_size(p) for p in claude_files]
    print(f"sizes:       {sizes}")
    print(f"size_sum:    {sum(sizes)}")
    print(f"size_mean:   {statistics.mean(sizes):.0f}")
    print(f"size_stdev:  {statistics.stdev(sizes):.0f}")
    print(f"size_cv%:    {100 * statistics.stdev(sizes) / statistics.mean(sizes):.1f}")
    claude_concat = concat(claude_files)
    claude_ts = count_timestamps(claude_concat)
    print(f"timestamps:  {claude_ts} / {src_ts}  ({100*claude_ts/src_ts:.1f}%)")
    claude_norm = normalize(claude_concat)
    src_norm = normalize(src_text)
    claude_match = claude_norm == src_norm
    print(f"content_eq:  {claude_match}")
    if not claude_match:
        print(f"  src_norm_chars: {len(src_norm)}, claude_norm_chars: {len(claude_norm)}")
    print()

    # --- Gemini
    gemini_files = sorted(GEMINI_DIR.glob("*gemini_part*.md"))
    print(f"=== Gemini ({len(gemini_files)} parts) ===")
    sizes_g = [file_size(p) for p in gemini_files]
    print(f"sizes:       {sizes_g}")
    print(f"size_sum:    {sum(sizes_g)}")
    if len(sizes_g) >= 2:
        print(f"size_mean:   {statistics.mean(sizes_g):.0f}")
        print(f"size_stdev:  {statistics.stdev(sizes_g):.0f}")
        print(f"size_cv%:    {100 * statistics.stdev(sizes_g) / statistics.mean(sizes_g):.1f}")
    gemini_concat = concat(gemini_files)
    gemini_ts = count_timestamps(gemini_concat)
    print(f"timestamps:  {gemini_ts} / {src_ts}  ({100*gemini_ts/src_ts:.1f}%)")
    gemini_norm = normalize(gemini_concat)
    gemini_match = gemini_norm == src_norm
    print(f"content_eq:  {gemini_match}")
    if not gemini_match:
        print(f"  src_norm_chars:    {len(src_norm)}")
        print(f"  gemini_norm_chars: {len(gemini_norm)}")
        print(f"  loss_chars:        {len(src_norm) - len(gemini_norm)} ({100*(len(src_norm)-len(gemini_norm))/len(src_norm):.1f}%)")
        # Lines in source not in gemini
        src_lines = set(src_norm.splitlines())
        gem_lines = set(gemini_norm.splitlines())
        only_src = src_lines - gem_lines
        only_gem = gem_lines - src_lines
        print(f"  lines_only_in_source: {len(only_src)}")
        print(f"  lines_only_in_gemini: {len(only_gem)}")
        if only_src:
            print(f"  sample_dropped_lines (first 5):")
            for ln in list(only_src)[:5]:
                preview = ln.encode("utf-8", "replace").decode("ascii", "replace")
                print(f"    - {preview[:120]}")


if __name__ == "__main__":
    split_gemini_output()
    main()
