#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log_file_op.py — 파일 이동·이름변경·복사·trash 이동 자동 로그 헬퍼
==================================================================

CLAUDE.md #16-C 의무 로그 시스템의 핵심 도구.

기능
----
- sha256·size 계산 → master.csv / master.jsonl / master.md 3개 형식에 동시 append
- (옵션) --execute 로 실제 이동/이름변경/복사 수행 (전후 sha256 무결성 검증)
- 공유드라이브(0.공유드라이브/) 경로는 #16-B 따라 쓰기·이동 차단

표준 필드 (1 작업 = 1 행)
-------------------------
timestamp, operation, source_path, dest_path, size_bytes, sha256, task_id, reason, verified

사용법
------
# (A) 이미 끝난 이동을 기록만 (dst 가 이미 존재)
python log_file_op.py --op move --src "원본경로" --dst "대상경로" \
    --reason "중복 정리" --task-id "sess-123"

# (B) 이동 실행 + 자동 로그 (전후 sha256 검증)
python log_file_op.py --op move --src "원본경로" --dst "대상경로" \
    --reason "중복 정리" --execute

# (C) trash 이동 (operation=delete-to-trash) + 실행
python log_file_op.py --op delete-to-trash --src "원본" \
    --dst "_trash/2026-06-15/원본" --reason "0바이트 빈 파일" --execute

operation 종류: move | rename | copy | delete-to-trash
"""
import argparse
import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------------------
# 경로 상수
# ---------------------------------------------------------------------------
WS_ROOT = Path(r"H:\내 드라이브")
LOG_DIR = WS_ROOT / ".agent" / "file_ops_log"
CSV_PATH = LOG_DIR / "master.csv"
JSONL_PATH = LOG_DIR / "master.jsonl"
MD_PATH = LOG_DIR / "master.md"

FIELDS = [
    "timestamp", "operation", "source_path", "dest_path",
    "size_bytes", "sha256", "task_id", "reason", "verified",
]
VALID_OPS = {"move", "rename", "copy", "delete-to-trash"}

# 공유드라이브 — 쓰기·이동 절대 금지 (#16-B)
SHARED_MARKERS = ("0.공유드라이브", "공유 드라이브", "shared drive")


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------
def is_shared(path: Path) -> bool:
    s = str(path).replace("\\", "/").lower()
    return any(m.lower() in s for m in SHARED_MARKERS)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    # 로컬 시간 ISO 8601 (초 단위, 기존 매니페스트 관례와 동일)
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# 로그 append
# ---------------------------------------------------------------------------
def append_csv(rec: dict) -> None:
    new_file = not CSV_PATH.exists()
    # 신규: Excel 호환 위해 BOM 포함 utf-8-sig + 헤더. 이후: 순수 utf-8 append.
    encoding = "utf-8-sig" if new_file else "utf-8"
    with open(CSV_PATH, "a", encoding=encoding, newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(rec)


def append_jsonl(rec: dict) -> None:
    with open(JSONL_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def append_md(rec: dict) -> None:
    new_file = not MD_PATH.exists()
    with open(MD_PATH, "a", encoding="utf-8") as f:
        if new_file:
            f.write(MD_HEADER)
        v = "OK" if rec["verified"] is True else (
            "FAIL" if rec["verified"] is False else "—")
        size = rec["size_bytes"] if rec["size_bytes"] is not None else "—"
        sha = (rec["sha256"][:12] + "…") if rec["sha256"] else "—"
        f.write(
            f"| {rec['timestamp']} | {rec['operation']} | "
            f"`{rec['source_path']}` | `{rec['dest_path']}` | {size} | "
            f"`{sha}` | {rec['task_id'] or '—'} | {rec['reason'] or '—'} | {v} |\n"
        )


MD_HEADER = """# 파일 이동·이름변경 마스터 로그 (사람 가독본)

> 자동 생성 — `.agent/scripts/log_file_op.py` 가 append.
> 기계 처리용 원본은 `master.jsonl`, 표 계산은 `master.csv` 참조.
> CLAUDE.md #16-C 의무 로그. 직접 손으로 수정하지 말 것.

| timestamp | operation | source | dest | size | sha256 | task_id | reason | verified |
|---|---|---|---|---|---|---|---|---|
"""


def write_log(rec: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    append_csv(rec)
    append_jsonl(rec)
    append_md(rec)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="파일 이동/이름변경 자동 로그")
    ap.add_argument("--op", required=True, choices=sorted(VALID_OPS),
                    help="작업 종류")
    ap.add_argument("--src", required=True, help="원본 경로")
    ap.add_argument("--dst", required=True, help="대상 경로 또는 신규 이름")
    ap.add_argument("--reason", default="", help="이동 사유 1줄")
    ap.add_argument("--task-id", default="", help="작업 세션 ID 또는 메모")
    ap.add_argument("--execute", action="store_true",
                    help="실제 이동/복사 수행 (전후 sha256 검증)")
    args = ap.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)

    # #16-B 공유드라이브 가드 — 쓰기 대상이 공유드라이브면 차단
    if args.execute and (is_shared(dst) or is_shared(src)):
        print("[차단] 공유드라이브(0.공유드라이브/) 경로는 이동·쓰기 금지 (#16-B). "
              "읽기·복사 외 작업은 사용자 직접 수행.", file=sys.stderr)
        return 2

    sha = None
    size = None
    verified = None  # None = 미검증, True/False = 검증 결과

    if args.execute:
        # 실행 모드: 사전 해시 → 이동/복사 → 사후 해시 대조
        if not src.exists():
            print(f"[오류] 원본 없음: {src}", file=sys.stderr)
            return 1
        if dst.exists():
            print(f"[오류] 대상 이미 존재(덮어쓰기 방지): {dst}", file=sys.stderr)
            return 1
        pre = sha256_of(src)
        size = src.stat().st_size
        dst.parent.mkdir(parents=True, exist_ok=True)
        if args.op == "copy":
            shutil.copy2(src, dst)
        else:  # move / rename / delete-to-trash
            shutil.move(str(src), str(dst))
        post = sha256_of(dst)
        sha = post
        verified = (pre == post)
        if not verified:
            print(f"[경고] sha256 불일치! pre={pre[:12]} post={post[:12]}",
                  file=sys.stderr)
    else:
        # 로그 전용 모드: dst 우선, 없으면 src 에서 해시·size 산출
        target = dst if dst.exists() else (src if src.exists() else None)
        if target is not None and target.is_file():
            sha = sha256_of(target)
            size = target.stat().st_size
            # dst·src 둘 다 있고 file이면 무결성 비교
            if dst.exists() and src.exists() and dst.is_file() and src.is_file():
                verified = (sha256_of(src) == sha256_of(dst))
            elif dst.exists():
                verified = True  # 대상 존재 = 이동 완료로 간주

    rec = {
        "timestamp": now_iso(),
        "operation": args.op,
        "source_path": str(src),
        "dest_path": str(dst),
        "size_bytes": size,
        "sha256": sha,
        "task_id": args.task_id,
        "reason": args.reason,
        "verified": verified,
    }
    write_log(rec)

    v = "검증OK" if verified is True else ("검증FAIL" if verified is False else "미검증")
    print(f"[로그완료] {args.op} | {v} | {src.name} → {dst} "
          f"| {LOG_DIR}\\master.(csv|jsonl|md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
