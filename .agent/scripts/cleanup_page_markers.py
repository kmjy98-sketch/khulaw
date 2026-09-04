"""
송영곤 쟁점노트 페이지 마커 OCR 아티팩트 정리 스크립트.

변환 대상 (라인 단위):
  > 416 | Part 1. 민법재산법
  > 628 I Part 2. 민법가족법
  28 | 민법재산법
  194 | Pal ：. 민법재샌법
  > 44 | .'i1. 민법재산법
  > 16 | Part 1. [민벱재산법
  ...

변환 후: `<!-- p.NNN -->`
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

DEFAULT_DIR = Path(vp("sync", "_교재원문", "민법", "송영곤_쟁점노트"))
WORKSPACE_ROOT = Path(VAULT_ROOT)

# 라인 전체가 페이지 푸터인 경우 매칭.
# 페이지번호(1~3자리) + 구분자 + 교재 식별어 포함, 전체 40자 이내.
PAGE_MARKER_RE = re.compile(
    r"^\s*(?:>\s*)?(\d{1,3})\s*[\|I]\s*.{0,40}?(?:민[법벱베]|재[산샌]|가족법|XH산|재\*)[^\n]*$"
)

# 페이지번호가 OCR에서 누락된 변종 푸터 (예: "I Part 1. 민법재산법").
# 번호를 알 수 없으므로 라인 삭제만 수행.
PAGE_MARKER_NONUM_RE = re.compile(
    r"^\s*(?:>\s*)?I\s*(?:Part|>|Par[ti!]?|Pal|'art|\.?'i)\s*\d*\.?\s*.{0,30}?(?:민[법벱베]|재[산샌]|가족법)[^\n]*$"
)

# 너무 긴 라인은 본문일 가능성이 크므로 배제.
MAX_LINE_LEN = 60


def process_file(path: Path) -> int:
    """한 파일 처리. 변경 수 반환."""
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    new_lines: list[str] = []
    changed = 0

    for line in lines:
        stripped = line.rstrip("\n").rstrip("\r")
        if len(stripped) <= MAX_LINE_LEN:
            m = PAGE_MARKER_RE.match(stripped)
            if m:
                page_num = m.group(1)
                if re.match(r"^\s*>", stripped):
                    new_lines.append(f"> <!-- p.{page_num} -->\n")
                else:
                    new_lines.append(f"<!-- p.{page_num} -->\n")
                changed += 1
                continue
            if PAGE_MARKER_NONUM_RE.match(stripped):
                # 번호 추정 불가 → 완전 제거 (blockquote면 `>`만 유지)
                if re.match(r"^\s*>", stripped):
                    new_lines.append(">\n")
                # blockquote가 아니면 라인 자체 제거
                changed += 1
                continue
        new_lines.append(line)

    if changed:
        new_content = "".join(new_lines)
        if new_content != original:
            # 백업 위치: _trash/{date}/pagemarker_cleanup/{상대경로}
            try:
                rel = path.relative_to(WORKSPACE_ROOT)
                backup = WORKSPACE_ROOT / "5.기타" / "_trash" / date.today().isoformat() / "pagemarker_cleanup" / rel
            except ValueError:
                backup = WORKSPACE_ROOT / "5.기타" / "_trash" / date.today().isoformat() / "pagemarker_cleanup" / path.name
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                shutil.copy2(path, backup)
            path.write_text(new_content, encoding="utf-8")

    return changed


def main(argv: list[str]) -> None:
    total_changed = 0
    total_files = 0

    if argv:
        target_dir = Path(argv[0])
        files = sorted(target_dir.rglob("*.md"))
        # 백업/휴지통/임시/원본 폴더 제외
        files = [
            f for f in files
            if not any(
                p.startswith("_backup") or p.startswith("_trash") or p.startswith(".")
                or p in ("_재추출", "_재추출본", "_raw", "_src", "_orig")
                for p in f.parts
            )
        ]
    else:
        target_dir = DEFAULT_DIR
        files = sorted(target_dir.glob("*.md"))

    for md in files:
        if md.name.endswith(".tmp.md"):
            continue
        count = process_file(md)
        if count:
            rel = md.relative_to(target_dir) if md.is_relative_to(target_dir) else md.name
            print(f"  [{count:>3}] {rel}")
            total_changed += count
            total_files += 1

    print(f"\n변경 파일 {total_files}개 / 총 교체 라인 {total_changed}건")


if __name__ == "__main__":
    main(sys.argv[1:])
