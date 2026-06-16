"""안 A 책 중심 재편 (1.민사). 강의 교재의 책→과목 직속 책이름폴더, 강의 부속→_강의/.
기본 DRY-RUN, --apply.
"""
import sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(r"H:\내 드라이브")
M = R / "1.민사"
APPLY = "--apply" in sys.argv
log = []

# (강의/교재 → 과목직속 책이름 폴더)
BOOK = [
    ("30.송영곤_기본민법/교재", "논점민법강의"),
    ("31.송영곤_사례/교재", "송영곤사례연습"),
    ("32.송영곤_사례연습2/교재", "민사법사례연습2"),
    ("33.송영곤_쟁노/교재", "민사법쟁점노트"),
]
# 강의 부속 폴더 → _강의/
COURSES = ["30.송영곤_기본민법", "31.송영곤_사례", "32.송영곤_사례연습2",
           "33.송영곤_쟁노", "34.송영곤_민소", "1-1_지난학기"]

ganui = M / "_강의"

# 1) 책(교재 내용) → 직속 책폴더
for src_rel, book in BOOK:
    src = M / src_rel
    if not src.exists():
        log.append(("교재없음", src_rel, "")); continue
    dst = M / book
    for f in sorted(src.glob("*.pdf")):
        d = dst / f.name
        if d.exists(): log.append(("대상존재", f.name, book)); continue
        log.append(("책이동", f"{src_rel}/{f.name}", f"{book}/"))
        if APPLY:
            dst.mkdir(parents=True, exist_ok=True); shutil.move(str(f), str(d))

# 2) 강의 부속 폴더 → _강의/
for c in COURSES:
    src = M / c
    if not src.exists():
        log.append(("강의없음", c, "")); continue
    dst = ganui / c
    log.append(("강의이동", c, f"_강의/{c}"))
    if APPLY:
        ganui.mkdir(exist_ok=True)
        if not dst.exists(): shutil.move(str(src), str(dst))

print(f"=== DRY-RUN={'OFF' if APPLY else 'ON'} | 1.민사 책중심 재편 ===")
from collections import Counter
print("유형:", dict(Counter(t for t, _, _ in log)))
print("\n[책 → 직속 책폴더]")
for t, a, b in log:
    if t == "책이동": print(f"  {a} → {b}")
print("\n[강의 부속 → _강의/]")
for t, a, b in log:
    if t == "강의이동": print(f"  {a} → {b}")
others = [(t, a, b) for t, a, b in log if t in ("교재없음", "대상존재", "강의없음")]
if others:
    print("\n[기타]")
    for t, a, b in others: print(f"  [{t}] {a} {b}")

# 적용 후 1.민사 직속 미리보기
if APPLY:
    print("\n=== 적용 후 1.민사 직속 ===")
    for p in sorted(M.iterdir()):
        if p.is_dir(): print(f"  {p.name}/")
