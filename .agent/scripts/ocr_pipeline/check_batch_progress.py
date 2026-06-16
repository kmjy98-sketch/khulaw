"""batch1 처리 진행 상황 확인."""
import json
from pathlib import Path

WORKSPACE = Path(r"H:\내 드라이브")
batch_index = WORKSPACE / ".agent/state/batch1_chunks.json"
rev_root = WORKSPACE / ".agent/data/ocr_chunks_reviewed"

batch = json.loads(batch_index.read_text(encoding="utf-8"))

reviewed = 0
missing = 0
missing_list = []

for r in batch:
    cp = r["chunk_path"]
    # .agent\data\ocr_chunks\subject\textbook\file  →  subject\textbook\file
    parts = cp.replace("\\", "/").split("/")
    rel = "/".join(parts[3:])  # skip .agent/data/ocr_chunks
    rev_path = rev_root / rel.replace("/", "\\")
    if rev_path.exists():
        reviewed += 1
    else:
        missing += 1
        missing_list.append(rel)

print(f"완료: {reviewed}/{len(batch)}")
print(f"미완료: {missing}")
if missing_list:
    print("미완료 목록 (첫 20개):")
    for p in missing_list[:20]:
        print(f"  {p}")
