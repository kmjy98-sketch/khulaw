"""batch2 전체 bucket 진행 현황 확인."""
import json
import os
import sys
from pathlib import Path

_p = os.path.abspath(__file__)
while os.path.basename(_p) != '.agent' and os.path.dirname(_p) != _p:
    _p = os.path.dirname(_p)
sys.path.insert(0, os.path.join(_p, 'scripts'))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

WORKSPACE = Path(VAULT_ROOT)
rev_root = WORKSPACE / ".agent/data/ocr_chunks_reviewed"

buckets = ["g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "g10"]

total_done = 0
total_all = 0
per_bucket = {}

for bucket in buckets:
    batch = json.loads((WORKSPACE / f".agent/state/batch2_{bucket}.json").read_text(encoding="utf-8"))
    reviewed = 0
    missing = []
    for r in batch:
        cp = r["chunk_path"]
        parts = cp.replace("\\", "/").split("/")
        rel = "/".join(parts[3:])
        rev_path = rev_root / rel.replace("/", "\\")
        if rev_path.exists():
            reviewed += 1
        else:
            missing.append(rel)
    per_bucket[bucket] = {"done": reviewed, "total": len(batch), "missing": missing}
    total_done += reviewed
    total_all += len(batch)

print(f"batch2 total: {total_done}/{total_all}")
print()
for b in buckets:
    d = per_bucket[b]
    status = "OK" if d["done"] == d["total"] else "PARTIAL"
    print(f"{b}: {d['done']}/{d['total']} [{status}]")
    if d["missing"]:
        subjects = {}
        for m in d["missing"]:
            subj = m.split("/")[0] if "/" in m else m.split("\\")[0]
            subjects[subj] = subjects.get(subj, 0) + 1
        print(f"  missing subjects: {subjects}")
        # sample
        for sample in d["missing"][:3]:
            print(f"    e.g. {sample}")
