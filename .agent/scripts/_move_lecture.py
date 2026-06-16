"""수업자료 → 강의자료/ 이동 (정찰 wb41ca4zq 의 moves 직접 적용).
폴더 내부 재배치(저위험·가역). 기본 DRY-RUN, --apply 시 실제 이동.
"""
import sys, json, os, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"H:\내 드라이브")
OUT = Path(r"C:\Users\111\AppData\Local\Temp\claude\H--------\20603c1d-acd0-40d1-ab66-0cfd1c7587a7\tasks\wb41ca4zq.output")
APPLY = "--apply" in sys.argv

data = json.loads(OUT.read_text(encoding="utf-8"))
plans = data["result"]["plans"]

total = 0
skips = []
print(f"=== 수업자료 이동 (DRY-RUN={'OFF' if APPLY else 'ON'}) ===\n")
for p in plans:
    folder = p["folder"]
    moves = p.get("moves", [])
    if not moves:
        print(f"[{folder}]  이동 0건  (수업자료 없음/이미정리)")
        continue
    # kind별 집계
    from collections import Counter
    kc = Counter(m["kind"].split("(")[0] for m in moves)
    print(f"[{folder}]  이동 {len(moves)}건  ({dict(kc)})")
    for m in moves:
        src = ROOT / m["from"].replace("/", os.sep)
        dst = ROOT / m["to"].replace("/", os.sep)
        if not src.exists():
            skips.append((m["from"], "원본없음")); continue
        if dst.exists():
            skips.append((m["from"], "대상존재")); continue
        if APPLY:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        total += 1

print(f"\n=== {'이동완료' if APPLY else '이동예정'} {total}건 | 건너뜀 {len(skips)}건 ===")
for f, why in skips[:30]:
    print(f"  [{why}] {f}")
