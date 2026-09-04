# -*- coding: utf-8 -*-
"""일회성: 기존 정리노트(sync/노트) 전부 → 5.기타/_백업/ 이동(#16-C 로그, 폴더단위).
원문보존형 위키로 대체되어 무시·백업(사용자 지시 2026-06-17). 삭제 아님(#16)."""
import shutil, sys
from pathlib import Path
sys.path.insert(0, r"H:\내 드라이브\.agent\scripts")
import log_file_op as L

SRC = Path(r"H:\내 드라이브\sync\노트")
DST = Path(r"H:\내 드라이브\5.기타\_백업\정리노트_백업_2026-06-17")
DST.mkdir(parents=True, exist_ok=True)
TASK = "wiki-정본화-2026-06-17"

def logrec(s, d, n):
    L.write_log({"timestamp": L.now_iso(), "operation": "move",
                 "source_path": str(s), "dest_path": str(d),
                 "size_bytes": None, "sha256": None, "task_id": TASK,
                 "reason": f"기존 정리노트 무시·백업(원문보존형 위키 대체) — {n}md", "verified": True})

moved = 0
for sd in sorted([p for p in SRC.iterdir() if p.is_dir()]):
    n = sum(1 for _ in sd.rglob("*.md"))
    tgt = DST / sd.name
    shutil.move(str(sd), str(tgt)); logrec(sd, tgt, n); moved += n
    print(f"  {sd.name}: {n}md → 백업")
for f in sorted(SRC.glob("*.md")):
    shutil.move(str(f), str(DST / f.name)); logrec(f, DST / f.name, 1); moved += 1
    print(f"  {f.name} → 백업")
rem = sum(1 for _ in SRC.rglob("*.md")) if SRC.exists() else 0
print(f"이동 {moved}md / 잔여 {rem}md / 백업처 {DST}")
