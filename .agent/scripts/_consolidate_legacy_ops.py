#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_consolidate_legacy_ops.py  (일회성)
기존 이동 매니페스트들을 read-only 로 읽어 표준 형식
(.agent/file_ops_log/_legacy_consolidated.csv) 으로 통합.

원본 매니페스트는 손대지 않는다(읽기만). #16 준수.
"""
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

WS = Path(VAULT_ROOT)
META = WS / "sync" / "_meta"
OUT = WS / ".agent" / "file_ops_log" / "_legacy_consolidated.csv"

FIELDS = ["timestamp", "operation", "source_path", "dest_path",
          "size_bytes", "sha256", "task_id", "reason", "verified"]

rows = []

# ── 출처 1: 중복정리 이동 매니페스트 (34건) ───────────────────────────
p1 = META / "중복정리_이동매니페스트_2026-04-30.json"
d1 = json.loads(p1.read_text(encoding="utf-8"))
ts1 = d1.get("timestamp", "2026-04-30T23:04:48")
for m in d1.get("moves", []):
    rows.append({
        "timestamp": ts1,
        "operation": "move",
        "source_path": m.get("src_path", ""),
        "dest_path": m.get("dst_path", ""),
        "size_bytes": m.get("src_size_before"),
        "sha256": m.get("src_body_hash_after_move") or m.get("src_body_hash_before", ""),
        "task_id": "중복정리_2026-04-30",
        "reason": "중복 본문 정리(" + d1.get("criterion", "") + ")",
        "verified": bool(m.get("body_unchanged", False)),
    })

# ── 출처 2: OCR 통합 매니페스트 moves (49건) ──────────────────────────
p2 = META / "_ocr_extracted_통합_매니페스트_2026-04-30_moves.json"
d2 = json.loads(p2.read_text(encoding="utf-8"))
for m in d2:
    dst = m.get("dst", "")
    op = "delete-to-trash" if "_trash" in dst.replace("\\", "/") else "move"
    rows.append({
        "timestamp": "2026-04-30T00:00:00",
        "operation": op,
        "source_path": m.get("src", ""),
        "dest_path": dst,
        "size_bytes": None,
        "sha256": m.get("body_hash_after") or m.get("raw_hash", ""),
        "task_id": "OCR통합_2026-04-30",
        "reason": "OCR 추출본 통합/" + m.get("status_tag", m.get("classification", "")),
        "verified": bool(m.get("body_hash_match", False)),
    })

# ── 출처 3: D2-D13 일괄처리 매니페스트 (MD 표, 4건) ──────────────────
d3 = [
    ("delete-to-trash", "content.txt (0바이트)",
     vp("_trash", "2026-06-15", "content.txt"), "0바이트 빈 파일(#16 이동)"),
    ("move", "기타서류\\ (행정서류 9)",
     vp("5.기타", "문서", "기타서류") + "\\", "행정서류 표준 위치(#42)"),
    ("move", "리퀴드텍스트 백업\\ (zip 2)",
     vp("5.기타", "_백업", "리퀴드텍스트 백업") + "\\", "앱 백업, 5.기타 집결"),
    ("move", "_종합본\\ (책별 합본 PDF 9)",
     vp("5.기타", "책 백업", "_종합본") + "\\", "D7·D12 집결, 백업 성격"),
]
for op, src, dst, reason in d3:
    rows.append({
        "timestamp": "2026-06-15T00:00:00",
        "operation": op,
        "source_path": src,
        "dest_path": dst,
        "size_bytes": None,
        "sha256": "",
        "task_id": "D2-D13_2026-06-15",
        "reason": reason,
        "verified": True,  # 매니페스트 기록상 sha256 전후 대조 OK
    })

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    for r in rows:
        if r["verified"] is not None:
            r = {**r, "verified": str(r["verified"]).lower()}
        w.writerow(r)

print(f"[통합완료] {len(rows)}건 → {OUT}")
print(f"  - 중복정리: {len(d1.get('moves', []))}건")
print(f"  - OCR통합: {len(d2)}건")
print(f"  - D2-D13: {len(d3)}건")
