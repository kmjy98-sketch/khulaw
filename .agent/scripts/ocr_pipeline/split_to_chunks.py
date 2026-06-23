"""md 파일 → 400행 청크 분할.

청크 규칙:
  - 첫 청크: frontmatter(--- ... ---) 전체 + 본문 시작부 포함
  - 페이지 마커(<!-- p.NNN -->) 경계를 우선적으로 분할점으로 사용
  - 마커 경계가 없으면 400행에서 강제 분할
  - 각 청크 파일에 chunk_meta 주석 삽입 (복원 시 사용)

출력: .agent/data/ocr_chunks/{subject}/{textbook}/{원파일명}__chunk_{NNN:03d}.md

입력:
  python split_to_chunks.py                        # all_files_index.json 전체
  python split_to_chunks.py --pilot                # pilot_files.json 대상만
  python split_to_chunks.py --file path/to/file.md # 단일 파일
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_p = os.path.abspath(__file__)
while os.path.basename(_p) != ".agent" and os.path.dirname(_p) != _p:
    _p = os.path.dirname(_p)
sys.path.insert(0, os.path.join(_p, "scripts"))
from _vault import VAULT_ROOT, vp  # noqa: E402

WORKSPACE_ROOT = Path(VAULT_ROOT)
CHUNKS_ROOT = WORKSPACE_ROOT / ".agent" / "data" / "ocr_chunks"
INDEX_PATH = WORKSPACE_ROOT / ".agent" / "state" / "all_files_index.json"
PILOT_PATH = WORKSPACE_ROOT / ".agent" / "state" / "pilot_files.json"
BATCH1_PATH = WORKSPACE_ROOT / ".agent" / "state" / "batch1_files.json"
BATCH2_PATH = WORKSPACE_ROOT / ".agent" / "state" / "batch2_files.json"
BATCH3_PATH = WORKSPACE_ROOT / ".agent" / "state" / "batch3_files.json"

CHUNK_SIZE = 400  # 목표 행 수
CHUNK_TOLERANCE = 40  # 마커 탐색 여유 (마커가 이 범위 안에 있으면 그 지점에서 분할)

PAGE_MARKER = re.compile(r"^<!--\s*p\.\d+\s*-->")
FRONTMATTER_SEP = re.compile(r"^---\s*$")


def extract_frontmatter(lines: list[str]) -> tuple[list[str], list[str]]:
    """frontmatter와 본문을 분리. frontmatter가 없으면 ([], lines)."""
    if not lines or not FRONTMATTER_SEP.match(lines[0]):
        return [], lines
    for i in range(1, len(lines)):
        if FRONTMATTER_SEP.match(lines[i]):
            return lines[: i + 1], lines[i + 1 :]
    return [], lines  # 닫히지 않은 frontmatter → 전체 본문으로


def find_split_point(lines: list[str], target: int) -> int:
    """target 행 근방에서 페이지 마커 기준 분할점 탐색. 없으면 target 반환."""
    lo = max(0, target - CHUNK_TOLERANCE)
    hi = min(len(lines), target + CHUNK_TOLERANCE)
    # target 이후 방향으로 먼저 탐색
    for i in range(target, hi):
        if PAGE_MARKER.match(lines[i]):
            return i
    # target 이전 방향 탐색
    for i in range(target - 1, lo - 1, -1):
        if PAGE_MARKER.match(lines[i]):
            return i
    return target


def split_file(md_path: Path) -> list[Path]:
    """파일을 청크로 분할하고 생성된 청크 경로 목록 반환."""
    text = md_path.read_text(encoding="utf-8", errors="replace")
    all_lines = text.splitlines(keepends=True)

    frontmatter, body = extract_frontmatter([l.rstrip("\n").rstrip("\r\n") for l in all_lines])
    fm_text = "\n".join(frontmatter) + ("\n" if frontmatter else "")

    # 출력 경로 계산
    rel = md_path.relative_to(WORKSPACE_ROOT / "sync" / "_교재원문")
    parts = rel.parts  # (subject, textbook, filename.md) or deeper
    subject = parts[0] if len(parts) >= 1 else "unknown"
    textbook = parts[1] if len(parts) >= 2 else "unknown"
    stem = md_path.stem

    out_dir = CHUNKS_ROOT / subject / textbook
    out_dir.mkdir(parents=True, exist_ok=True)

    # 기존 청크 삭제 (재실행 멱등)
    for old in out_dir.glob(f"{stem}__chunk_*.md"):
        old.unlink()

    chunks: list[Path] = []
    pos = 0
    chunk_idx = 0

    while pos < len(body):
        if pos + CHUNK_SIZE >= len(body):
            # 마지막 청크
            chunk_body = body[pos:]
            end = len(body)
        else:
            split_at = find_split_point(body, pos + CHUNK_SIZE)
            chunk_body = body[pos:split_at]
            end = split_at

        # chunk_meta 주석 (파일 맨 첫 줄에 삽입)
        meta_comment = (
            f"<!-- chunk_meta: file={md_path.name} idx={chunk_idx:03d}"
            f" lines={pos}-{end-1} -->\n"
        )

        # 첫 청크에는 frontmatter 포함
        if chunk_idx == 0 and frontmatter:
            content = fm_text + meta_comment + "\n".join(chunk_body)
        else:
            content = meta_comment + "\n".join(chunk_body)

        out_path = out_dir / f"{stem}__chunk_{chunk_idx:03d}.md"
        out_path.write_text(content, encoding="utf-8")
        chunks.append(out_path)

        pos = end
        chunk_idx += 1

    return chunks


def load_file_list(pilot: bool, batch: bool = False, batch2: bool = False, batch3: bool = False) -> list[Path]:
    if batch3:
        index_file = BATCH3_PATH
    elif batch2:
        index_file = BATCH2_PATH
    elif batch:
        index_file = BATCH1_PATH
    elif pilot:
        index_file = PILOT_PATH
    else:
        index_file = INDEX_PATH
    if not index_file.exists():
        print(f"인덱스 파일 없음: {index_file}")
        sys.exit(1)
    records = json.loads(index_file.read_text(encoding="utf-8"))
    return [WORKSPACE_ROOT / r["path"] for r in records]


def main() -> None:
    pilot_mode = "--pilot" in sys.argv
    batch_mode = "--batch" in sys.argv
    batch2_mode = "--batch2" in sys.argv
    batch3_mode = "--batch3" in sys.argv
    single_file = None
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        single_file = Path(sys.argv[idx + 1])

    if single_file:
        files = [single_file]
    else:
        files = load_file_list(pilot=pilot_mode, batch=batch_mode, batch2=batch2_mode, batch3=batch3_mode)

    total_chunks = 0
    chunk_index: list[dict] = []

    for f in files:
        if not f.exists():
            print(f"  건너뜀 (파일 없음): {f}")
            continue
        chunks = split_file(f)
        total_chunks += len(chunks)
        for c in chunks:
            chunk_index.append({
                "chunk_path": str(c.relative_to(WORKSPACE_ROOT)),
                "source_path": str(f.relative_to(WORKSPACE_ROOT)),
            })
        print(f"  {f.name} → {len(chunks)} 청크")

    # 청크 인덱스 저장
    if pilot_mode:
        ci_name = "pilot_chunks.json"
    elif batch3_mode:
        ci_name = "batch3_chunks.json"
    elif batch2_mode:
        ci_name = "batch2_chunks.json"
    elif batch_mode:
        ci_name = "batch1_chunks.json"
    else:
        ci_name = "all_chunks.json"
    ci_path = WORKSPACE_ROOT / ".agent" / "state" / ci_name
    ci_path.write_text(json.dumps(chunk_index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n총 {total_chunks} 청크 → {ci_path}")


if __name__ == "__main__":
    main()
