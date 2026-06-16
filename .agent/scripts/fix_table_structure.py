"""fix_table_structure.py — 기존 추출 마크다운 파일 대상 표 구조 복원 + 문맥 끊김 수정.

대상: sync/_교재원문/ 하위 .md 파일 (OCR 또는 pypdf 추출본)

처리 항목:
  1. 암묵적 표 탐지 → 마크다운 표 변환
     - OCR에서 스페이스/탭으로 구분된 다중 컬럼 행
     - 2열 이상 + 3행 이상 연속 패턴
  2. 페이지 경계 문맥 끊김 복원
     - --- Page N --- 전후에서 종결기호 없는 이전 줄 + 조사 시작 다음 줄 → 연결

사용법:
  python fix_table_structure.py                      # 전체 교재원문
  python fix_table_structure.py --dir "경로"         # 특정 디렉토리
  python fix_table_structure.py --file "파일.md"     # 단일 파일
  python fix_table_structure.py --dry-run            # 변경 없이 미리보기
"""
from __future__ import annotations

import re
import shutil
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

WORKSPACE_ROOT = Path(r"H:\내 드라이브")
DEFAULT_ROOT = Path(r"H:\내 드라이브\sync\_교재원문")

# ── 공통 패턴 ──────────────────────────────────────────────────
_SENT_END = re.compile(r'[.!?）\]】」』다함음됨임없있]\s*$')
_CONN_START = re.compile(r'^[의를이가은는에서도과와로으부터까지만도]')
_PAGE_RE = re.compile(r'\n\n--- Page (\d+) ---\n')
_BLOCK_START = re.compile(r'^\s*(?:#{1,6}\s|-\s|\*\s|>\s|\||\d+\.\s|[①-⑳])')

# ── 1. 페이지 경계 문맥 복원 ────────────────────────────────────

def repair_page_boundaries(text: str) -> tuple[str, int]:
    """반환: (수정된 텍스트, 복원 건수)"""
    parts = _PAGE_RE.split(text)
    if len(parts) <= 1:
        return text, 0

    out = [parts[0]]
    repairs = 0
    idx = 1
    while idx < len(parts):
        page_num = parts[idx]
        page_text = parts[idx + 1] if idx + 1 < len(parts) else ""
        idx += 2

        prev_last = out[-1].rstrip().split("\n")[-1] if out[-1].strip() else ""
        next_first = page_text.lstrip().split("\n")[0] if page_text.strip() else ""

        if (prev_last and next_first
                and not _SENT_END.search(prev_last)
                and _CONN_START.match(next_first)
                and not _BLOCK_START.match(next_first)):
            out[-1] = out[-1].rstrip() + page_text
            repairs += 1
        else:
            out.append(f"\n\n--- Page {page_num} ---\n")
            out.append(page_text)

    return "".join(out), repairs


# ── 2. 암묵적 표 탐지 및 마크다운 변환 ────────────────────────

# 2+ 개의 연속 공백으로 나뉘는 컬럼 패턴
_COL_SEP = re.compile(r'  {2,}|\t+')

# 마크다운 구조 줄이면 건드리지 않음
_MD_STRUCT = re.compile(r'^\s*(?:#{1,6}\s|-\s|\*\s|>\s|\||\[|\d+\.\s|```)')


def _split_cols(line: str) -> list[str]:
    """공백 2+ 개 또는 탭으로 셀 분리."""
    parts = _COL_SEP.split(line.strip())
    return [p.strip() for p in parts if p.strip()]


def _looks_like_table_row(line: str, min_cols: int = 2) -> bool:
    """표 행처럼 보이는지 (이미 마크다운 표이거나 구조 태그면 제외)."""
    if _MD_STRUCT.match(line):
        return False
    if line.strip().startswith("|"):
        return False  # 이미 마크다운 표
    cols = _split_cols(line)
    return len(cols) >= min_cols


def _align_cols(rows_cols: list[list[str]]) -> list[list[str]]:
    """컬럼 수를 최대값으로 맞춤."""
    n = max(len(r) for r in rows_cols)
    return [r + [""] * (n - len(r)) for r in rows_cols]


def _make_md_table(rows_cols: list[list[str]]) -> str:
    rows = _align_cols(rows_cols)
    n = len(rows[0])
    header = "| " + " | ".join(rows[0]) + " |"
    sep = "| " + " | ".join(["---"] * n) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows[1:])
    if body:
        return "\n".join([header, sep, body])
    return "\n".join([header, sep])


def convert_implicit_tables(text: str, min_rows: int = 3) -> tuple[str, int]:
    """
    연속 min_rows개 이상의 다중 컬럼 행 → 마크다운 표.
    반환: (수정된 텍스트, 변환된 표 개수)
    """
    lines = text.split("\n")
    out: list[str] = []
    table_count = 0

    i = 0
    while i < len(lines):
        line = lines[i]

        # 표 후보 행 시작 탐지
        if _looks_like_table_row(line):
            run = [line]
            j = i + 1
            while j < len(lines) and _looks_like_table_row(lines[j]):
                run.append(lines[j])
                j += 1

            if len(run) >= min_rows:
                # 각 행을 컬럼으로 분리
                rows_cols = [_split_cols(r) for r in run]
                # 컬럼 수가 일관적인지 확인 (최빈값 ±1 허용)
                col_counts = [len(r) for r in rows_cols]
                most_common = max(set(col_counts), key=col_counts.count)
                if most_common >= 2 and col_counts.count(most_common) >= min_rows:
                    out.append(_make_md_table(rows_cols))
                    table_count += 1
                    i = j
                    continue
                # 기준 미달 → 원문 그대로
                out.extend(run)
                i = j
                continue

        out.append(line)
        i += 1

    return "\n".join(out), table_count


# ── 3. 파일 처리 ───────────────────────────────────────────────

def process_file(path: Path, dry_run: bool = False) -> dict:
    original = path.read_text(encoding="utf-8")
    text = original

    text, page_repairs = repair_page_boundaries(text)
    text, table_converts = convert_implicit_tables(text)

    changes = page_repairs + table_converts
    if changes == 0 or text == original:
        return {"file": path.name, "page_repairs": 0, "tables": 0, "changed": False}

    if not dry_run:
        # 백업
        try:
            rel = path.relative_to(WORKSPACE_ROOT)
            backup = WORKSPACE_ROOT / "5.기타" / "교재원문_백업" / date.today().isoformat() / "table_fix" / rel
        except ValueError:
            backup = WORKSPACE_ROOT / "5.기타" / "교재원문_백업" / date.today().isoformat() / "table_fix" / path.name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(text, encoding="utf-8")

    return {"file": path.name, "page_repairs": page_repairs, "tables": table_converts, "changed": True}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="표 구조 복원 + 페이지 경계 문맥 복원")
    parser.add_argument("--dir", default=None, help="대상 디렉토리 (기본: sync/_교재원문)")
    parser.add_argument("--file", default=None, help="단일 파일 처리")
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 미리보기")
    args = parser.parse_args()

    if args.file:
        files = [Path(args.file)]
    else:
        target = Path(args.dir) if args.dir else DEFAULT_ROOT
        files = sorted(target.rglob("*.md"))
        files = [
            f for f in files
            if not any(
                p.startswith("_backup") or p.startswith("_trash") or p.startswith(".")
                or p in ("_재추출", "_재추출본", "_raw", "_src", "_orig")
                for p in f.parts
            )
        ]

    total_files = 0
    total_pages = 0
    total_tables = 0

    for md in files:
        result = process_file(md, dry_run=args.dry_run)
        if result["changed"]:
            prefix = "[DRY]" if args.dry_run else "     "
            print(f"{prefix} {result['file']}  "
                  f"페이지복원={result['page_repairs']}  표변환={result['tables']}")
            total_files += 1
            total_pages += result["page_repairs"]
            total_tables += result["tables"]

    print(f"\n변경 파일 {total_files}개 | 페이지 복원 {total_pages}건 | 표 변환 {total_tables}건")


if __name__ == "__main__":
    main()
