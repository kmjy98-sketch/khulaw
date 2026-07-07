"""강의통합 되돌리기: 강의/교재/{독해책} → 과목 루트 독립폴더. 빈 35.송영곤_선택 정리.
독해책=과목 루트 독립폴더 원칙 복원. 원본은 10.도서관 유지. 기본 DRY-RUN, --apply.
"""
import sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(r"H:\내 드라이브")
TRASH = R / "_trash/2026-06-14/빈_강의폴더"
APPLY = "--apply" in sys.argv

# (현재 강의/교재/{책} 경로, 독립 목적지)
MOVES = [
    ("1.민사/송영곤_기본민법/교재/논점재산법", "1.민사/논점재산법"),
    ("1.민사/31.송영곤_사례/교재/송영곤사례연습", "1.민사/송영곤사례연습"),
    ("1.민사/33.송영곤_쟁노/교재/민사법쟁점노트", "1.민사/민사법쟁점노트"),
    ("1.민사/34.송영곤_민소/교재/민소사례", "1.민사/민소사례"),
    ("1.민사/34.송영곤_민소/교재/논점민소", "1.민사/논점민소"),
    ("1.민사/35.송영곤_선택/교재/신민사법선택형", "1.민사/신민사법선택형"),
    ("2.형사/김기용_형법교안/교재/김기용형총", "2.형사/김기용형총"),
]

log = []
for src_rel, dst_rel in MOVES:
    src, dst = R / src_rel, R / dst_rel
    if not src.exists():
        log.append((src_rel, "원본없음")); continue
    if dst.exists():
        log.append((src_rel, f"대상존재:{dst_rel}")); continue
    n = len(list(src.glob("*.pdf")))
    log.append((src_rel, f"→ {dst_rel} ({n}p)"))
    if APPLY:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

# 빈 35.송영곤_선택 / 빈 교재 정리
empties = []
for c in ["1.민사/35.송영곤_선택"]:
    d = R / c
    if d.exists():
        files = [p for p in d.rglob("*") if p.is_file()]
        if not files:
            empties.append(c)
            if APPLY:
                TRASH.mkdir(parents=True, exist_ok=True)
                shutil.move(str(d), str(TRASH / d.name))

print(f"=== DRY-RUN={'OFF(적용)' if APPLY else 'ON'} ===")
for a, b in log:
    print(f"  {a}  {b}")
print(f"빈 강의폴더 정리: {empties}")
