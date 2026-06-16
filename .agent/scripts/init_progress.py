#!/usr/bin/env python3
"""
init_progress.py — Drive 폴더 스캔 → .auto-memory/ocr_progress.json 초기 생성.

사용법:
  python init_progress.py
  python init_progress.py --drive-root "H:/내 드라이브"
  python init_progress.py --dry-run
  python init_progress.py --force      # 기존 파일 덮어쓰기
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE               = os.environ.get("MEMORY_BASE", r"H:\내 드라이브\.auto-memory")
PROGRESS_FILE      = os.path.join(BASE, "ocr_progress.json")
DRIVE_ROOT_DEFAULT = r"H:\내 드라이브"
SYNC_ROOT_DEFAULT  = r"H:\내 드라이브\sync\_교재원문"

PAGE_RANGE_RE  = re.compile(r'_p(\d+)-(\d+)\.(?:md|qmd)$')
SUBJECT_DIR_RE = re.compile(r'^\d+\.')


def scan_pdfs(drive_root: str) -> dict:
    """과목 폴더(1.민사/ 2.형사/ …)에서 PDF 스캔"""
    books = {}
    for d in sorted(Path(drive_root).iterdir()):
        if not d.is_dir() or not SUBJECT_DIR_RE.match(d.name):
            continue
        for pdf in sorted(d.rglob("*.pdf")):
            book_id = pdf.stem
            if book_id in books:
                book_id = f"{book_id}__{pdf.parent.name}"
            books[book_id] = {
                "pdf_path"         : str(pdf),
                "subject"          : d.name,
                "status"           : "pending",
                "pages_done"       : [],
                "in_progress_chunk": 0,
                # marker-pdf 전환 후에도 ocr_progress.json 의 기존 키 호환을 위해 유지.
                # 신규 파이프라인은 .auto-memory/ocr_state/progress.json 을 별도로 사용.
                "paddle_dir"       : None,
                "md_chunks"        : [],
            }
    return books


def scan_md_chunks(sync_root: str) -> dict:
    """sync/_교재원문/ .md 파일에서 책 stem → 페이지 범위 매핑"""
    md_map = {}
    root = Path(sync_root)
    if not root.exists():
        return md_map
    for md in sorted(root.rglob("*.md")):
        m = PAGE_RANGE_RE.search(md.name)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            stem = PAGE_RANGE_RE.sub('', md.name)
            md_map.setdefault(stem, []).append({"path": str(md), "start": start, "end": end})
    return md_map


def match_books(books: dict, md_map: dict) -> dict:
    """PDF 책 ID와 MD 파일 파일명 패턴 기반 매핑"""
    for book_id, info in books.items():
        if book_id in md_map:
            info["md_chunks"] = sorted(md_map[book_id], key=lambda x: x["start"])
            continue
        # 토큰 겹침 기반 부분 매핑 (2토큰 이상)
        book_tokens = set(book_id.lower().split("_"))
        best_stem, best_score = None, 0
        for stem, _ in md_map.items():
            overlap = len(book_tokens & set(stem.lower().split("_")))
            if overlap > best_score and overlap >= 2:
                best_score, best_stem = overlap, stem
        if best_stem:
            info["md_chunks"]        = sorted(md_map[best_stem], key=lambda x: x["start"])
            info["md_stem_matched"]  = best_stem
    return books


def main():
    parser = argparse.ArgumentParser(description="OCR progress.json 초기 생성")
    parser.add_argument("--drive-root", default=DRIVE_ROOT_DEFAULT)
    parser.add_argument("--sync-root",  default=SYNC_ROOT_DEFAULT)
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--force",      action="store_true", help="기존 파일 덮어쓰기")
    args = parser.parse_args()

    if os.path.exists(PROGRESS_FILE) and not args.force:
        print(f"이미 존재: {PROGRESS_FILE}")
        print("  --force 플래그로 덮어쓸 수 있습니다.")
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            prog = json.load(f)
        by_status = {}
        for v in prog.get("books", {}).values():
            s = v.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
        print(f"  현황: {by_status}")
        return

    print(f"스캔: {args.drive_root}")
    books = scan_pdfs(args.drive_root)
    print(f"  PDF 발견: {len(books)}권")

    print(f"스캔: {args.sync_root}")
    md_map = scan_md_chunks(args.sync_root)
    print(f"  MD 청크: {sum(len(v) for v in md_map.values())}개")

    books = match_books(books, md_map)
    matched   = sum(1 for v in books.values() if v["md_chunks"])
    unmatched = sum(1 for v in books.values() if not v["md_chunks"])
    print(f"  매핑 성공: {matched}권 / 미매핑: {unmatched}권")

    if unmatched > 0:
        print("  [미매핑 목록]")
        for book_id, info in books.items():
            if not info["md_chunks"]:
                print(f"    - {book_id} ({info['subject']})")

    progress = {
        "version": 1,
        "created": datetime.now().isoformat(),
        "last_run": None,
        "books": books,
    }

    if args.dry_run:
        print(f"\n[DRY-RUN] Would write: {PROGRESS_FILE} ({len(books)}권)")
        return

    os.makedirs(BASE, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
    print(f"\n생성 완료: {PROGRESS_FILE}")


if __name__ == "__main__":
    main()
