"""batch2 교재 키 확인."""
import json
from pathlib import Path
from collections import Counter

WS = Path(r"H:\내 드라이브")
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
