"""재구조: 완전원본→7.도서관/, 강의중복 독해책 splits→{강의}/교재/{책}/, 빈 책폴더→_trash.
기본 DRY-RUN, --apply 시 실제. 이동만.
"""
import sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(r"H:\내 드라이브")
LIB = R / "10.도서관"
TRASH = R / "_trash/2026-06-14/빈_책폴더"
APPLY = "--apply" in sys.argv

# 완전 원본(통합본) 26개 — 도서관行
ORIGINALS = {
    "compact형법총론OX_26.pdf", "강성민_헌법_최종정리_OX_기본권_25.pdf", "강성민_헌법_최종정리_OX_총론통치구조_25.pdf",
    "김기용_형법총론_교안_26.pdf", "김준호_민법강의_물권_26.pdf", "김준호_민법강의_민총_26.pdf",
    "김준호_민법강의_채각_26.pdf", "김준호_민법강의_채총_26.pdf", "논점민법강의_재산법_26.pdf",
    "논점민소_원본_26.pdf", "민사례1_원본_26.pdf", "민사법쟁점노트_소송집행_26.pdf",
    "민사법쟁점노트_재산법_26.pdf", "민소사례_원본_26.pdf", "반반형법_원본_26.pdf",
    "송영곤_사례연습_물권_26.pdf", "송영곤_사례연습_민총_26.pdf", "송영곤_사례연습_채권_26.pdf",
    "송영곤_신민사법선택형연습1_가족법_26.pdf", "송영곤_신민사법선택형연습1_물권법_26.pdf",
    "송영곤_신민사법선택형연습1_민법총칙_26.pdf", "송영곤_신민사법선택형연습1_채권법1_26.pdf",
    "송영곤_신민사법선택형연습1_채권법2_26.pdf", "유니온헌_원본_27.pdf", "작은변사기형법_25.pdf",
    "해커스헌_원본_27.pdf",
}
# 강의 중복책: 책폴더 → 통합 강의폴더 (splits는 {강의}/교재/{책}/)
COURSE = {
    ("1.민사", "논점민소"): "1.민사/34.송영곤_민소",
    ("1.민사", "민소사례"): "1.민사/34.송영곤_민소",
    ("1.민사", "논점재산법"): "1.민사/송영곤_기본민법",
    ("1.민사", "송영곤사례연습"): "1.민사/31.송영곤_사례",
    ("1.민사", "신민사법선택형"): "1.민사/35.송영곤_선택",
    ("1.민사", "민사법쟁점노트"): "1.민사/33.송영곤_쟁노",
    ("2.형사", "김기용형총"): "2.형사/김기용_형법교안",
}
# 비강의 단독책: splits 과목루트 유지, 원본만 도서관
NONCOURSE = [
    ("1.민사", "김준호민법강의"), ("1.민사", "민사례1"),
    ("2.형사", "반반형법"), ("2.형사", "작은변사기"), ("2.형사", "compact형총OX"),
    ("3.공법", "강성민헌법OX"), ("3.공법", "유니온헌강"), ("3.공법", "해커스헌강"), ("3.공법", "헌법300"),
]

logL, logS, logE = [], [], []  # 도서관, splits이동, 빈폴더


def mv(src, dst, log):
    if dst.exists():
        log.append((str(src.relative_to(R)), "대상존재-SKIP")); return
    log.append((str(src.relative_to(R)), str(dst.relative_to(R))))
    if APPLY:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))


allbooks = list(COURSE.keys()) + NONCOURSE
for subj, book in allbooks:
    folder = R / subj / book
    if not folder.exists():
        continue
    for f in sorted(folder.glob("*.pdf")):
        if f.name in ORIGINALS:
            mv(f, LIB / f.name, logL)               # 원본 → 도서관
        elif (subj, book) in COURSE:
            course = R / COURSE[(subj, book)]
            mv(f, course / "교재" / book / f.name, logS)  # splits → 강의/교재/책/
        # NONCOURSE splits는 제자리 유지
    # 강의중복책 폴더가 비면 _trash
    if (subj, book) in COURSE and folder.exists():
        remain = list(folder.glob("*"))
        if not remain or (APPLY and not list(folder.iterdir())):
            logE.append(str(folder.relative_to(R)))
            if APPLY and not any(folder.iterdir()):
                shutil.move(str(folder), str(TRASH / book))

print(f"=== DRY-RUN={'OFF(적용)' if APPLY else 'ON'} ===")
print(f"\n[원본 → 7.도서관] ({len(logL)})")
for a, b in logL[:30]: print(f"  {a.split(chr(92))[-1]}")
print(f"\n[강의중복 splits → 강의/교재/책] ({len(logS)})")
from collections import Counter
c = Counter(b.rsplit("\\", 2)[0] if "대상" not in b else b for _, b in logS)
for k, v in c.items(): print(f"  {k}: {v}개")
print(f"\n[빈 책폴더 → _trash] ({len(logE)}): {logE}")
