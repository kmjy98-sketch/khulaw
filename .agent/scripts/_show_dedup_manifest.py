import json
import sys
import os
from pathlib import Path

# UTF-8 출력 강제
sys.stdout.reconfigure(encoding="utf-8")

p = Path(r"H:\내 드라이브\sync\_meta\_ocr_extracted_통합_매니페스트_2026-04-30.json")
data = json.loads(p.read_text(encoding="utf-8"))
print("counts:", data["counts"])
print()
for r in data["plan"]:
    name = os.path.basename(r["raw_path"])[:80]
    print(f"  [{r['classification']:>10}] {name}")
    bm = r.get("best_match")
    bm_short = os.path.basename(bm) if bm else "-"
    print(f"      best={r.get('best_match_ratio',0):.2%} union={r.get('union_ratio',0):.2%}  match={bm_short}")
    print(f"      reason={r['reason'][:120]}")
