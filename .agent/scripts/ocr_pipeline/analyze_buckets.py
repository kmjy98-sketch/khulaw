"""batch2 bucket별 과목/교재 분포 분석."""
import json
import os
import sys
from pathlib import Path
_p = os.path.abspath(__file__)  # noqa: E402
while os.path.basename(_p) != '.agent' and os.path.dirname(_p) != _p:  # noqa: E402
    _p = os.path.dirname(_p)  # noqa: E402
sys.path.insert(0, os.path.join(_p, 'scripts'))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

WORKSPACE = Path(VAULT_ROOT)
rev_root = WORKSPACE / ".agent/data/ocr_chunks_reviewed"

buckets = ["g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9", "g10"]

print("=== Subject distribution per bucket ===")
for b in buckets:
    g = json.loads((WORKSPACE / f".agent/state/batch2_{b}.json").read_text(encoding="utf-8"))
    subjects = {}
    for r in g:
        cp = r["chunk_path"]
        parts = cp.replace("\\", "/").split("/")
        subj = parts[3] if len(parts) > 3 else "?"
        subjects[subj] = subjects.get(subj, 0) + 1
    print(f"{b}: {dict(sorted(subjects.items()))}")

print()
print("=== g7 textbooks (all partial) ===")
g7 = json.loads((WORKSPACE / ".agent/state/batch2_g7.json").read_text(encoding="utf-8"))
textbooks = {}
for r in g7:
    cp = r["chunk_path"]
    parts = cp.replace("\\", "/").split("/")
    if len(parts) > 4:
        textbooks[parts[4]] = textbooks.get(parts[4], 0) + 1
for t, c in sorted(textbooks.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}")

print()
print("=== g7 processed vs missing per textbook ===")
for r in g7:
    pass

g7_done = {}
g7_missing = {}
for r in g7:
    cp = r["chunk_path"]
    parts = cp.replace("\\", "/").split("/")
    rel = "/".join(parts[3:])
    rev_path = rev_root / rel.replace("/", "\\")
    tb = parts[4] if len(parts) > 4 else "?"
    if rev_path.exists():
        g7_done[tb] = g7_done.get(tb, 0) + 1
    else:
        g7_missing[tb] = g7_missing.get(tb, 0) + 1

for tb in sorted(set(list(g7_done.keys()) + list(g7_missing.keys()))):
    print(f"  {tb}: done={g7_done.get(tb, 0)} missing={g7_missing.get(tb, 0)}")
