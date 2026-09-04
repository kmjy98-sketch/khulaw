"""미처리 batch1 청크 목록을 missing_chunks.json으로 저장."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

WORKSPACE = Path(VAULT_ROOT)
batch_index = WORKSPACE / ".agent/state/batch1_chunks.json"
rev_root = WORKSPACE / ".agent/data/ocr_chunks_reviewed"
out_path = WORKSPACE / ".agent/state/missing_chunks.json"

batch = json.loads(batch_index.read_text(encoding="utf-8"))

missing = []
for r in batch:
    cp = r["chunk_path"]
    parts = cp.replace("\\", "/").split("/")
    rel = "/".join(parts[3:])
    rev_path = rev_root / rel.replace("/", "\\")
    if not rev_path.exists():
        missing.append(r)

out_path.write_text(json.dumps(missing, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"미처리: {len(missing)}개 → {out_path}")
for r in missing:
    print(f"  {r['chunk_path']}")
