#!/usr/bin/env python3
"""
haiku_ocr_correct.py — Claude Code 에서 실행하는 OCR 교정 카운터/디스패처
(marker-pdf 파이프라인용).

ocr_compare_v2.ipynb 가 생성한 corrections.jsonl 의 Class 1 (text) 항목 중
아직 교정되지 않은 라인 수를 집계하고, Cowork/Claude Code 측에서 처리할
대상 목록을 출력한다. 실제 LLM 교정은 Cowork agent 가 담당 (이 스크립트는
API 호출을 하지 않는다 — Claude Code Max 플랜 내에서 처리).

사용법:
  python .agent/scripts/haiku_ocr_correct.py
  python .agent/scripts/haiku_ocr_correct.py --book {교재명}    # 특정 교재만 표시

  또는 Cowork에서: "OCR 교정 진행해줘" → 이 스크립트의 출력을 보고 sub-agent spawn.
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
CORRECTIONS_DIR = os.path.join(BASE, "ocr_state", "corrections")
LEGACY_DIR      = os.path.join(BASE, "corrections")


def _resolve_dirs() -> list:
    dirs = []
    if os.path.isdir(CORRECTIONS_DIR):
        dirs.append(CORRECTIONS_DIR)
    if os.path.isdir(LEGACY_DIR) and LEGACY_DIR != CORRECTIONS_DIR:
        if any(p.endswith(".jsonl") for p in os.listdir(LEGACY_DIR)):
            dirs.append(LEGACY_DIR)
    return dirs


def _is_pending_text(entry: dict) -> bool:
    """Class 1 (텍스트) 미교정 항목인가?"""
    kind = entry.get("kind") or entry.get("type")
    if kind not in ("text", "text_conflict"):
        return False
    if entry.get("class") not in (1, None):
        return False
    correction = entry.get("correction") or {}
    if correction.get("corrected"):
        return False
    if entry.get("status") in ("applied", "haiku_done", "reviewed"):
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="OCR 교정 대상 집계 (marker-pdf 파이프라인)")
    parser.add_argument("--book", help="특정 교재만 표시")
    args = parser.parse_args()

    dirs = _resolve_dirs()
    if not dirs:
        print(f"corrections 디렉터리 없음: {CORRECTIONS_DIR}")
        print("  ocr_compare_v2.ipynb 의 Cell 2 (run_compare) 를 먼저 실행하세요.")
        return

    jsonl_files = []
    for d in dirs:
        jsonl_files.extend(sorted(glob.glob(os.path.join(d, "*.jsonl"))))
    if not jsonl_files:
        print(f"corrections 파일 없음: {dirs}")
        return

    by_book = {}
    sample = {}
    for jf in jsonl_files:
        book = Path(jf).stem
        if args.book and book != args.book:
            continue
        with open(jf, "r", encoding="utf-8") as f:
            items = [json.loads(l) for l in f if l.strip()]
        pending = [it for it in items if _is_pending_text(it)]
        if pending:
            by_book[book] = len(pending)
            sample[book] = pending[:2]

    if not by_book:
        print("교정 대상 없음 (모두 처리 완료 또는 corrections 비어 있음).")
        for d in dirs:
            print(f"  - {d}")
        return

    total = sum(by_book.values())
    print(f"교정 대상 총 {total}건 / 교재 {len(by_book)}개")
    print("-" * 80)
    for book, n in sorted(by_book.items(), key=lambda x: -x[1]):
        print(f"  {book[:50]:50s}  {n:6d} 건")
        for it in sample[book]:
            old = (it.get("old") or it.get("original", "") or "")[:60]
            new = (it.get("new") or it.get("paddle", "") or "")[:60]
            print(f"      old: {old}")
            print(f"      new: {new}")

    print()
    print("실행 방법:")
    print("  1. Cowork 에서 'OCR 교정 진행해줘' → Claude 가 sub-agent 로 처리")
    print("  2. 또는 Claude Code 에서 직접 conflict 라인을 보여주고 교정 요청")
    print()
    print("교정 결과는 각 항목에 다음 필드로 추가:")
    print('  "correction": {"corrected": "...", "confidence": 0.0~1.0, "changed": bool}')
    print('  "status": "haiku_done"')


if __name__ == "__main__":
    main()
