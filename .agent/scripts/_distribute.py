"""작업용 책 폴더 → 과목 루트 분산(+원본 동봉), 지난학기 강의 → {과목}/1-1_지난학기/.
기본 DRY-RUN, --apply 시 실제 이동. 이동만(삭제 없음).
"""
import sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(r"H:\내 드라이브")
W = R / "작업용"
TRASH = R / "_trash/2026-06-14"
APPLY = "--apply" in sys.argv

SUBJECT = {
    "김준호민법강의": "1.민사", "논점민소": "1.민사", "논점재산법": "1.민사", "민사례1": "1.민사",
    "민사법쟁점노트": "1.민사", "민소사례": "1.민사", "송영곤사례연습": "1.민사", "신민사법선택형": "1.민사",
    "김기용형총": "2.형사", "반반형법": "2.형사", "작은변사기": "2.형사", "compact형총OX": "2.형사",
    "강성민헌법OX": "3.공법", "유니온헌": "3.공법", "해커스헌": "3.공법", "헌법300": "3.공법",
}
KEYMAP = [  # (_원본 파일명 키워드, book) — 구체적인 것 먼저
    ("신민사법선택형", "신민사법선택형"), ("송영곤_사례연습", "송영곤사례연습"), ("김준호", "김준호민법강의"),
    ("논점민법강의_재산법", "논점재산법"), ("논점재산법", "논점재산법"), ("논점민소", "논점민소"),
    ("민사법사례연습1", "민사례1"), ("민사례1", "민사례1"), ("민사법쟁점노트", "민사법쟁점노트"),
    ("민소사례", "민소사례"), ("헌법핵심정리300", "헌법300"), ("헌법300", "헌법300"),
    ("해커스헌", "해커스헌"), ("유니온헌", "유니온헌"), ("강성민", "강성민헌법OX"),
    ("반반형법", "반반형법"), ("compact형법총론OX", "compact형총OX"), ("김기용", "김기용형총"),
    ("작은변사기", "작은변사기"),
]
PAST = {
    "1.민사": ["10.강혜림_민법1", "20.전경운_민법3"],
    "2.형사": ["20.서보학_형법1", "30.홍형철_기본형법", "40.김성돈_형법총론"],
    "3.공법": ["10.이진_헌법원리1", "20.강성민_행정법"],
    "4.선택법": ["10.법조윤리", "20.국제법총론"],
}


def mv(src: Path, dst: Path, log):
    if dst.exists():
        log.append((str(src.relative_to(R)), "대상존재-SKIP")); return
    log.append((str(src.relative_to(R)), str(dst.relative_to(R))))
    if APPLY:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))


log1, log2, log3, log4 = [], [], [], []
# Phase 1: 책 폴더 분산
for book, subj in SUBJECT.items():
    src = W / book
    if src.exists():
        mv(src, R / subj / book, log1)
# Phase 1b: _원본 → 각 책 폴더
orig = W / "_원본"
if orig.exists():
    for f in sorted(orig.glob("*.pdf")):
        book = next((b for kw, b in KEYMAP if kw in f.name), None)
        if not book:
            log2.append((f.name, "??미매칭")); continue
        mv(f, R / SUBJECT[book] / book / f.name, log2)
# Phase 2: 지난학기
for subj, lects in PAST.items():
    for lect in lects:
        src = R / subj / lect
        if src.exists():
            mv(src, R / subj / "1-1_지난학기" / lect, log3)
# cleanup 빈 stub
for stub in [W / "고동성 찌라시"]:
    if stub.exists() and not any(stub.iterdir()):
        mv(stub, TRASH / ("빈_" + stub.name), log4)

print(f"=== DRY-RUN={'OFF(적용)' if APPLY else 'ON'} ===")
print(f"\n[1] 책 폴더 분산 ({len(log1)})")
for a, b in log1: print(f"  {a}  →  {b}")
print(f"\n[1b] _원본 동봉 ({len(log2)})")
for a, b in log2: print(f"  {a}  →  {b}")
print(f"\n[2] 지난학기 이동 ({len(log3)})")
for a, b in log3: print(f"  {a}  →  {b}")
print(f"\n[정리] 빈 stub ({len(log4)}): {[a for a,_ in log4]}")
mism = [a for a, b in log2 if b == "??미매칭"]
if mism: print(f"\n⚠ _원본 미매칭: {mism}")
