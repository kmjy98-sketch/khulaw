"""batch2 교재 키 확인."""
import os
import sys
import json
from pathlib import Path
from collections import Counter

_p = os.path.abspath(__file__)
while os.path.basename(_p) != '.agent' and os.path.dirname(_p) != _p:
    _p = os.path.dirname(_p)
sys.path.insert(0, os.path.join(_p, 'scripts'))
from _vault import VAULT_ROOT, vp  # noqa: E402

WS = Path(VAULT_ROOT)
chunks = json.loads((WS / ".agent/state/batch2_chunks.json").read_text(encoding="utf-8"))

by_tb = Counter()
for r in chunks:
    parts = r["chunk_path"].split("\\")
    if len(parts) >= 5:
        key = f"{parts[3]}/{parts[4]}"
        by_tb[key] += 1

for k, v in sorted(by_tb.items(), key=lambda x: -x[1]):
    print(f"{k}: {v}개")
print(f"\n합계: {sum(by_tb.values())}개")
