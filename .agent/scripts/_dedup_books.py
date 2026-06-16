"""송영곤 3책 중복 단일화 + 혼입 정리. canonical=장분할 독해본, 강의 교재/ 안.
기본 DRY-RUN, --apply.
"""
import sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(r"H:\내 드라이브")
T = R / "_trash/2026-06-14/책중복단일화"
APPLY = "--apply" in sys.argv
log = []


def mv(src, dst):
    if not src.exists():
        log.append(("없음", str(src.relative_to(R)), "")); return
    if dst.exists():
        log.append(("대상존재", str(src.relative_to(R)), str(dst.relative_to(R)))); return
    log.append(("이동", str(src.relative_to(R)), str(dst.relative_to(R))))
    if APPLY:
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(src), str(dst))


def trash(p, tag):
    if not p.exists(): return
    log.append(("trash", str(p.relative_to(R)), tag))
    if APPLY:
        T.mkdir(parents=True, exist_ok=True)
        d = T / p.name
        if not d.exists(): shutil.move(str(p), str(d))


# ===== 1) 논점민법강의 (30.기본민법/교재) =====
g = R / "1.민사/30.송영곤_기본민법/교재"
bn = g / "_분할"
bunhal_stems = set()
for f in bn.glob("*.pdf"):
    a = f.stem.rsplit("_", 1)
    if a[1].isdigit(): bunhal_stems.add(a[0])
for f in sorted(g.glob("논점민법강의_*.pdf")):
    st = f.stem
    if "_p001-050" in st: trash(f, "슬라이스")
    elif "판례색인" in st or "민법입문" in st: pass  # 유지
    elif st in bunhal_stems: trash(f, "편본(↔_분할)")
# _분할 → 교재/ flat
for f in sorted(bn.glob("*.pdf")): mv(f, g / f.name)
if APPLY and bn.exists() and not any(bn.iterdir()):
    bn.rmdir()
trash(R / "1.민사/논점재산법", "독립 부분권(논점민법강의 subset)")

# ===== 2) 민법 사례연습 (31.사례) — 교재 기존 정리 먼저, 독립본 나중 =====
g31 = R / "1.민사/31.송영곤_사례/교재"
ga31 = R / "1.민사/31.송영곤_사례/강의자료"
minso = R / "1.민사/34.송영곤_민소/강의자료/보충자료"
jaeng = R / "1.민사/33.송영곤_쟁노/강의자료"
TEXTBOOK6 = {f"송영곤_사례연습_{x}_26.pdf" for x in ["목차", "민총", "채권", "담보", "물권", "가족"]}
KEEP_PARTS = ("계약", "민총", "채권", "담보", "물권", "가족", "목차")
# (a) 31/교재 기존 편본 trash + 혼입 분리 (독립본 이동 전에)
for f in sorted(g31.glob("*.pdf")):
    n = f.name
    if n in TEXTBOOK6: trash(f, "편본(↔독립 장분할 완본)")
    elif "민소" in n and "해설" in n: mv(f, minso / n)          # 민소 다른책
    elif "쟁점노트" in n: mv(f, jaeng / n)                      # 쟁점노트 수정
    elif n.startswith("송영곤_사례연습_") and not n.split("_")[2].startswith(KEEP_PARTS):
        mv(f, ga31 / n)                                          # 손필기 등
    elif n.startswith("송영곤_") and ("보강" in n or "보충" in n or "수정자료" in n): mv(f, ga31 / n)
trash(g31 / "_분할", "채권 재분할(중복)")
# (b) 송영곤사례연습(15, 완본) → 31/교재
for f in sorted((R / "1.민사/송영곤사례연습").glob("*.pdf")): mv(f, g31 / f.name)
if APPLY and (R / "1.민사/송영곤사례연습").exists() and not any((R / "1.민사/송영곤사례연습").iterdir()):
    (R / "1.민사/송영곤사례연습").rmdir()

# ===== 3) 민사법쟁점노트 (33.쟁노) — 교재 기존 trash 먼저, 독립본 나중 =====
g33 = R / "1.민사/33.송영곤_쟁노/교재"
# (a) 33/교재 기존 편본(목차·가족법·재산법·소송집행) + _분할 trash
for f in sorted(g33.glob("민사법쟁점노트_*.pdf")): trash(f, "편본(↔독립 완본14)")
trash(g33 / "_분할", "재분할(중복)")
# (b) 민사법쟁점노트(14, 목차+가족법+재산법장+소송집행장 = 완본) → 33/교재
for f in sorted((R / "1.민사/민사법쟁점노트").glob("*.pdf")): mv(f, g33 / f.name)
if APPLY and (R / "1.민사/민사법쟁점노트").exists() and not any((R / "1.민사/민사법쟁점노트").iterdir()):
    (R / "1.민사/민사법쟁점노트").rmdir()

print(f"=== DRY-RUN={'OFF' if APPLY else 'ON'} | 총 {len(log)} ===")
from collections import Counter
print("유형:", dict(Counter(t for t, _, _ in log)))
for t, a, b in log:
    print(f"  [{t}] {a}" + (f" → {b}" if b else ""))
