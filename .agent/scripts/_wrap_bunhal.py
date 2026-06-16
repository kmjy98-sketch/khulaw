"""교재/_분할의 흩어진 분할책 파트를 책ID 하위폴더로 감싸 보관(이동만). _tmp txt는 _trash.
"""
import sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(r"H:\내 드라이브")
TRASH = R / "_trash/2026-06-14/분할잔재"

# (_분할폴더, 하위폴더명, 파일명포함문자열)
GROUPS = [
    ("1.민사/94.교재/_분할", "송영곤_기록형연습1_23", "기록형"),
    ("1.민사/94.교재/_분할", "송영곤_선택형연습1_26", "선택형연습1"),
    ("1.민사/94.교재/_분할_1", "송영곤_요건사실론", "요건사실론"),
    ("2.형사/94.교재/_분할", "COMPACT형법", "COMPACT"),
    ("3.공법/94.교재/_분할", "2027해커스헌법사례형", "해커스"),
    ("3.공법/94.교재/_분할", "유니온헌법기출편", "유니온"),
    ("3.공법/94.교재/_분할", "핵심정리300", "핵심정리300"),
]

for folder, sub, key in GROUPS:
    d = R / folder
    if not d.exists():
        print(f"[없음] {folder}"); continue
    target = d / sub
    moved = 0
    for f in sorted(d.glob("*.pdf")):
        if key in f.name:
            target.mkdir(exist_ok=True)
            t = target / f.name
            if not t.exists():
                shutil.move(str(f), str(t)); moved += 1
    print(f"[{folder}/{sub}/] {moved}개")

# _tmp txt 잔재 → _trash
for txt in (R / "3.공법/94.교재/_분할").glob("_tmp_*.txt"):
    TRASH.mkdir(parents=True, exist_ok=True)
    shutil.move(str(txt), str(TRASH / txt.name)); print(f"[trash] {txt.name}")
print("분할책 폴더화 완료")
