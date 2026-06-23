"""batch2_chunks.json을 에이전트 그룹별 서브인덱스로 분할 (중복 없음)."""
import json
import os
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

WS = Path(VAULT_ROOT)
state = WS / ".agent" / "state"
chunks = json.loads((state / "batch2_chunks.json").read_text(encoding="utf-8"))

by_tb = defaultdict(list)
for r in chunks:
    parts = r["chunk_path"].split("\\")
    if len(parts) >= 5:
        key = (parts[3], parts[4])
        by_tb[key].append(r)

sorted_tb = sorted(by_tb.items(), key=lambda x: -len(x[1]))

def save(name: str, records: list) -> None:
    p = state / f"batch2_{name}.json"
    p.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  batch2_{name}.json: {len(records)}개")

# 1위 교재 3등분 (g1/g2/g3)
top1 = sorted_tb[0][1]
n = len(top1)
save("g1", top1[:n//3])
save("g2", top1[n//3:2*n//3])
save("g3", top1[2*n//3:])

# 2위 교재 2등분 (g4/g5)
top2 = sorted_tb[1][1]
n2 = len(top2)
save("g4", top2[:n2//2])
save("g5", top2[n2//2:])

# 3위 단독 (g6)
save("g6", sorted_tb[2][1])

# 4+5위 합산 (g7)
save("g7", sorted_tb[3][1] + sorted_tb[4][1])

# 6+7+8위 중 비형법만 (g8)
g8 = []
for (subj, tb), recs in sorted_tb[5:8]:
    if subj != "형법":
        g8.extend(recs)
save("g8", g8)

# 나머지 민법+헌법 (g9): sorted_tb[8:]에서 민법/헌법만
g9 = []
for (subj, tb), recs in sorted_tb[8:]:
    if subj in ("민법", "헌법"):
        g9.extend(recs)
save("g9", g9)

# 형법 전체 (g10)
g10 = []
for (subj, tb), recs in sorted_tb:
    if subj == "형법":
        g10.extend(recs)
save("g10", g10)

# 검증: 중복 없이 전체 커버
covered = set()
for name in ["g1","g2","g3","g4","g5","g6","g7","g8","g9","g10"]:
    p = state / f"batch2_{name}.json"
    recs = json.loads(p.read_text(encoding="utf-8"))
    for r in recs:
        covered.add(r["chunk_path"])
print(f"\n전체: {len(chunks)}개, 커버: {len(covered)}개")
if len(covered) != len(chunks):
    # 누락 찾기
    all_paths = {r["chunk_path"] for r in chunks}
    missing = all_paths - covered
    extra = covered - all_paths
    print(f"  누락: {len(missing)}개, 중복/초과: {len(extra)}개")
    for p in list(missing)[:5]:
        print(f"    누락: {p.split(chr(92))[-2]}/{p.split(chr(92))[-1]}")
