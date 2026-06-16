"""청크 재병합 + 원본 md 파일 백업 후 교체.

흐름:
  1. pilot_chunks.json (또는 all_chunks.json)에서 소스별로 청크를 그룹화
  2. 각 청크에 대해:
     - rejected_chunks.json에 있으면 → 원본 청크 사용
     - 없으면 → 검토본 청크 사용
  3. 청크 순서대로 concat (chunk_meta 주석 제거)
  4. 원본 .md 파일 → 5.기타/_trash/{date}/ocr_llm_review/{상대경로} 백업
  5. 병합 결과로 교체

사용:
  python merge_and_apply.py --pilot [--dry-run]
  python merge_and_apply.py --all [--dry-run]
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

WORKSPACE_ROOT = Path(r"H:\내 드라이브")
CHUNKS_ROOT = WORKSPACE_ROOT / ".agent" / "data" / "ocr_chunks"
REVIEWED_ROOT = WORKSPACE_ROOT / ".agent" / "data" / "ocr_chunks_reviewed"
TRASH_BASE = WORKSPACE_ROOT / "5.기타" / "_trash"

CHUNK_META = re.compile(r"<!--\s*chunk_meta:.*?-->\n?")


def load_rejected_set(pilot: bool) -> set[str]:
    rp = WORKSPACE_ROOT / ".agent" / "state" / "rejected_chunks.json"
    if not rp.exists():
        return set()
    records = json.loads(rp.read_text(encoding="utf-8"))
    return {r["chunk_path"] for r in records}


def get_chunk_text(chunk_path: Path, rev_path: Path, rejected: set[str], rel_key: str) -> str:
    if rel_key in rejected or not rev_path.exists():
        text = chunk_path.read_text(encoding="utf-8", errors="replace")
    else:
        text = rev_path.read_text(encoding="utf-8", errors="replace")
    # chunk_meta 주석 제거
    return CHUNK_META.sub("", text)


def merge_source(
    source_path: str,
    chunk_records: list[dict],
    rejected: set[str],
    dry_run: bool,
    trash_date: str,
) -> bool:
    """단일 소스 파일의 청크를 병합·교체. 성공 여부 반환."""
    # 청크 정렬 (파일명의 chunk_NNN 기준)
    def chunk_idx(rec: dict) -> int:
        m = re.search(r"__chunk_(\d+)\.md$", rec["chunk_path"])
        return int(m.group(1)) if m else 0

    chunk_records.sort(key=chunk_idx)

    merged_parts = []
    for rec in chunk_records:
        chunk_abs = WORKSPACE_ROOT / rec["chunk_path"]
        rev_rel = Path(rec["chunk_path"]).relative_to(".agent/data/ocr_chunks")
        rev_abs = REVIEWED_ROOT / rev_rel
        text = get_chunk_text(chunk_abs, rev_abs, rejected, rec["chunk_path"])
        merged_parts.append(text)

    merged = "\n".join(merged_parts)
    # 연속 빈 줄 3개 이상 → 2개로 정리
    merged = re.sub(r"\n{4,}", "\n\n\n", merged)

    src_abs = WORKSPACE_ROOT / source_path

    if dry_run:
        print(f"  [DRY-RUN] {src_abs.name}: {len(chunk_records)} 청크 병합 예정")
        return True

    # 백업
    trash_dir = TRASH_BASE / trash_date / "ocr_llm_review"
    rel_to_sync = src_abs.relative_to(WORKSPACE_ROOT / "sync")
    backup_path = trash_dir / rel_to_sync
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_abs, backup_path)

    # 교체
    src_abs.write_text(merged, encoding="utf-8")
    print(f"  완료: {src_abs.name} ({len(chunk_records)} 청크, 백업 → {backup_path.parent})")
    return True


def main() -> None:
    pilot_mode = "--pilot" in sys.argv
    batch_mode = "--batch" in sys.argv
    batch2_mode = "--batch2" in sys.argv
    batch3_mode = "--batch3" in sys.argv
    dry_run = "--dry-run" in sys.argv

    if pilot_mode:
        chunks_index_path = WORKSPACE_ROOT / ".agent" / "state" / "pilot_chunks.json"
    elif batch3_mode:
        chunks_index_path = WORKSPACE_ROOT / ".agent" / "state" / "batch3_chunks.json"
    elif batch2_mode:
        chunks_index_path = WORKSPACE_ROOT / ".agent" / "state" / "batch2_chunks.json"
    elif batch_mode:
        chunks_index_path = WORKSPACE_ROOT / ".agent" / "state" / "batch1_chunks.json"
    else:
        chunks_index_path = WORKSPACE_ROOT / ".agent" / "state" / "all_chunks.json"

    if not chunks_index_path.exists():
        print(f"청크 인덱스 없음: {chunks_index_path}")
        sys.exit(1)

    records = json.loads(chunks_index_path.read_text(encoding="utf-8"))
    rejected = load_rejected_set(pilot_mode)

    # 소스 파일별로 그룹화
    by_source: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_source[rec["source_path"]].append(rec)

    trash_date = date.today().isoformat()
    success = failed = 0

    print(f"{'[DRY-RUN] ' if dry_run else ''}병합 대상: {len(by_source)} 파일")
    for src, chunks in by_source.items():
        try:
            ok = merge_source(src, chunks, rejected, dry_run, trash_date)
            if ok:
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  오류 {src}: {e}")
            failed += 1

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}완료: {success}개 성공, {failed}개 실패")

    if not dry_run:
        # 청크 임시 폴더 정리 여부 안내 (자동 삭제 안 함 — 수동 확인 후)
        print(f"\n임시 청크 폴더: {CHUNKS_ROOT}")
        print("확인 후 수동으로 정리하세요 (자동 삭제 안 함)")


if __name__ == "__main__":
    main()
