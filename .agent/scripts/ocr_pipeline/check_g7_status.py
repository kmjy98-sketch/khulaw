"""g7 bucket 실제 처리 상태 확인 (src/reviewed 파일명 비교)."""
import json
from pathlib import Path

WORKSPACE = Path(r"H:\내 드라이브")
rev_root = WORKSPACE / ".agent/data/ocr_chunks_reviewed"

g7 = json.loads((WORKSPACE / ".agent/state/batch2_g7.json").read_text(encoding="utf-8"))

print(f"g7 entries: {len(g7)}")
print()

# 샘플 경로 출력
for r in g7[:3]:
    print("chunk_path:", repr(r["chunk_path"]))
print()

# textbook별로 상태 확인
from collections import defaultdict
tb_src = defaultdict(list)
tb_rev = defaultdict(list)
tb_miss = defaultdict(list)

for r in g7:
    cp = r["chunk_path"]
    parts = cp.replace("\\", "/").split("/")
    rel = "/".join(parts[3:])
    tb = parts[4] if len(parts) > 4 else "?"
    rev_path = rev_root / rel.replace("/", "\\")
    tb_src[tb].append(rel)
    if rev_path.exists():
        tb_rev[tb].append(rel)
    else:
        tb_miss[tb].append((rel, str(rev_path)))

for tb in sorted(set(tb_src.keys())):
    print(f"{tb}: src={len(tb_src[tb])} reviewed={len(tb_rev[tb])} missing={len(tb_miss[tb])}")
    if tb_miss[tb]:
        print("  missing samples (src rel, expected rev path):")
        for rel, rpath in tb_miss[tb][:3]:
            print(f"    rel: {rel}")
            print(f"    rev: {rpath}")
            print(f"    rev.exists: {Path(rpath).exists()}")
