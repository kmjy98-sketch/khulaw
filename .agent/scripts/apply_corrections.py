#!/usr/bin/env python3
"""
apply_corrections.py — 검토 통과한 교정을 실제 .md 파일에 적용 (marker-pdf 파이프라인).

스키마 (ocr_compare_v2.ipynb 출력):
  {"file": "<old md path>", "page": N, "line": <file-relative idx>,
   "class": 1|2|3, "kind": "text"|"table_adopt"|"orphan",
   "old": "...", "new": "...", "cer": float, "confidence": float,
   "anchor_count": int, "diff_size": int,
   "op": "replace|insert|delete|table_replace",
   "status": "pending|haiku_done|reviewed|applied",
   "verified": null|true|false,
   "correction": {"corrected": "...", "confidence": float, "changed": bool}?,
   "review":     {"final": "...", "approved": bool}?}

적용 기준:
  - kind == "table_adopt"    : new 본문으로 교체, old 는 HTML 주석 보존 (status != applied 인 모든 항목).
  - kind == "text", class==1 : confidence ≥ AUTO_APPLY_THRESHOLD AND correction.changed → 자동 적용.
  - kind == "text", class==1 : status == reviewed AND review.approved      → 적용.
  - class == 2               : verified != true 면 스킵 (anchor 검증 미완).
  - kind == "orphan"         : 자동 적용 안 함 (수동 확인).

원본 보존: 적용된 라인은 `<!-- original: ... -->` 주석으로 직전에 보존 (CLAUDE.md #15).

사용법:
  python apply_corrections.py
  python apply_corrections.py --dry-run
  python apply_corrections.py --confidence-threshold 0.9
"""

import os
import sys
import json
import glob
import argparse
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE            = os.environ.get("MEMORY_BASE", r"H:\내 드라이브\.auto-memory")
PROGRESS_FILE   = os.path.join(BASE, "ocr_progress.json")
# marker-pdf 파이프라인: ocr_compare_v2.ipynb 가 사용하는 경로
CORRECTIONS_DIR = os.path.join(BASE, "ocr_state", "corrections")
# 구 PaddleOCR 경로 (fallback): 마이그레이션 미완 시 함께 스캔
LEGACY_DIR      = os.path.join(BASE, "corrections")

AUTO_APPLY_THRESHOLD = 0.85

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from legal_regex import is_anchor_line


def _resolve_corrections_dirs() -> list:
    dirs = []
    if os.path.isdir(CORRECTIONS_DIR):
        dirs.append(CORRECTIONS_DIR)
    if os.path.isdir(LEGACY_DIR) and LEGACY_DIR != CORRECTIONS_DIR:
        # legacy 가 비어 있으면 무시
        if any(p.endswith(".jsonl") for p in os.listdir(LEGACY_DIR)):
            dirs.append(LEGACY_DIR)
    return dirs


def _apply_table_adopt(item: dict, dry_run: bool, threshold: float) -> bool:
    """marker-pdf 신스키마: kind == 'table_adopt' — new 본문으로 통째 교체."""
    chunk_path = item.get("file") or item.get("chunk_path")
    if not chunk_path or not os.path.exists(chunk_path):
        return False

    new_content = item.get("new") or item.get("paddle_content") or ""
    if not new_content.strip():
        return False

    with open(chunk_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 위치: 신스키마는 line(파일 기준 0-based)만 가짐.
    # old 본문 길이만큼 앞으로 카운트해서 교체 범위 산정.
    start = int(item.get("line", 0))
    old_content = item.get("old") or ""
    old_n_lines = len(old_content.splitlines())
    end = min(len(lines) - 1, start + max(0, old_n_lines - 1))

    if start < 0 or start >= len(lines):
        return False

    orig = "".join(lines[start:end + 1]).rstrip("\n")
    replacement = f"<!-- original:\n{orig}\n-->\n{new_content.rstrip()}\n"
    new_lines = lines[:start] + [replacement] + lines[end + 1:]

    if dry_run:
        print(f"  [DRY] table_adopt: {chunk_path} (lines {start}-{end})")
        return True
    with open(chunk_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return True


def _apply_text_corrections(chunk_path: str, items: list, dry_run: bool) -> int:
    """라인 교정: 신스키마 kind == 'text' (class==1) 항목들.

    적용 우선순위:
      review.final  →  correction.corrected  →  new (compare-만 통과)
    """
    if not chunk_path or not os.path.exists(chunk_path):
        return 0
    with open(chunk_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    applied = 0
    for it in sorted(items, key=lambda x: int(x.get("line", 0)), reverse=True):
        line_idx = int(it.get("line", -1))
        if line_idx < 0 or line_idx >= len(lines):
            continue
        original_line = lines[line_idx].rstrip("\n")
        # anchor 라인은 별도 검증(verified) 없으면 건드리지 않음.
        if it.get("class") == 2 and it.get("verified") is not True:
            continue
        if is_anchor_line(original_line) and it.get("verified") is not True:
            continue

        final = (
            (it.get("review") or {}).get("final")
            or (it.get("correction") or {}).get("corrected")
            or it.get("new")
            or original_line
        )
        if final == original_line:
            continue
        lines[line_idx] = f"<!-- original: {original_line} -->\n{final}\n"
        applied += 1

    if dry_run:
        print(f"  [DRY] text corrections: {chunk_path} ({applied}건)")
        return applied
    if applied > 0:
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    return applied


def _is_table_appliable(item: dict) -> bool:
    if item.get("status") == "applied":
        return False
    kind = item.get("kind") or item.get("type")
    return kind == "table_adopt"


def _is_text_appliable(item: dict, threshold: float) -> bool:
    if item.get("status") == "applied":
        return False
    kind = item.get("kind") or item.get("type")
    if kind not in ("text", "text_conflict"):
        return False
    cls = item.get("class")
    if cls == 3:
        return False
    if cls == 2 and item.get("verified") is not True:
        return False

    review = item.get("review") or {}
    if item.get("status") == "reviewed" and review.get("approved"):
        return True

    correction = item.get("correction") or {}
    conf = item.get("confidence")
    if conf is None:
        conf = correction.get("confidence", 0.0)

    if item.get("status") in ("haiku_done", "reviewed") \
            and conf >= threshold \
            and correction.get("changed"):
        return True

    # compare 단독에서 confidence ≥ threshold 인 텍스트는 안전하지 않으므로 제외.
    return False


def main():
    parser = argparse.ArgumentParser(description="OCR 교정 적용 (marker-pdf 파이프라인)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confidence-threshold", type=float,
                        default=AUTO_APPLY_THRESHOLD)
    args = parser.parse_args()

    dirs = _resolve_corrections_dirs()
    if not dirs:
        print(f"corrections 디렉터리 없음: {CORRECTIONS_DIR}")
        sys.exit(1)

    jsonl_files = []
    for d in dirs:
        jsonl_files.extend(sorted(glob.glob(os.path.join(d, "*.jsonl"))))
    if not jsonl_files:
        print(f"corrections 파일 없음: {dirs}")
        sys.exit(1)

    print(f"교재 파일: {len(jsonl_files)}개  (dirs: {dirs})")

    total_tables  = 0
    total_lines   = 0
    applied_books = set()

    for jf in jsonl_files:
        book_id = Path(jf).stem
        with open(jf, "r", encoding="utf-8") as f:
            items = [json.loads(l) for l in f if l.strip()]

        table_items = [i for i in items if _is_table_appliable(i)]
        text_items  = [i for i in items if _is_text_appliable(i, args.confidence_threshold)]

        if not table_items and not text_items:
            continue

        print(f"  {book_id}: table_adopt {len(table_items)}건 / text {len(text_items)}건")

        for item in table_items:
            if _apply_table_adopt(item, args.dry_run, args.confidence_threshold):
                item["status"] = "applied"
                total_tables  += 1
                applied_books.add(book_id)

        # text: file 별로 묶어 한 번에 적용
        by_file = {}
        for item in text_items:
            cp = item.get("file") or item.get("chunk_path", "")
            by_file.setdefault(cp, []).append(item)
        for chunk_path, corrs in by_file.items():
            n = _apply_text_corrections(chunk_path, corrs, args.dry_run)
            total_lines += n
            if not args.dry_run and n > 0:
                for c in corrs:
                    c["status"] = "applied"
                applied_books.add(book_id)

        if not args.dry_run:
            with open(jf, "w", encoding="utf-8") as f:
                for item in items:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")

    if not args.dry_run and os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                progress = json.load(f)
            for bid in applied_books:
                if bid in progress.get("books", {}):
                    progress["books"][bid]["status"] = "applied"
            with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[경고] progress 갱신 실패: {e}")

    print(f"\n적용 완료: 표 {total_tables}건 / 라인 {total_lines}건")


if __name__ == "__main__":
    main()
