# -*- coding: utf-8 -*-
"""교재 카드화 커버리지 감사: OCR(후보) vs 정본카드(02_cards_v37) vs 구intake(02_cards) vs _trash. 누락서적 도출. 읽기전용."""
import os, re, sys, glob
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = VAULT_ROOT
OCR = f"{WS}/outputs/01_ocr_llamaparse"
V37 = f"{WS}/outputs/02_cards_v37"
OLD = f"{WS}/outputs/02_cards"
TRASH = f"{WS}/_trash"


def book_of(fn):
    """파일명에서 책 식별자 추출: _llamaparse 또는 _p{digit} 또는 _cards 이전."""
    b = re.split(r"_llamaparse|_p\d|_cards", fn)[0]
    return b.rstrip("_")


def collect(d, pat="*.md"):
    c = defaultdict(int)
    if not os.path.isdir(d):
        return c
    for f in os.listdir(d):
        if f.endswith(".md"):
            c[book_of(f)] += 1
    return c


ocr = collect(OCR)
v37 = collect(V37)
old = collect(OLD)

# _trash 안의 카드md (재귀)
trash = defaultdict(int)
for f in glob.glob(f"{TRASH}/**/*_cards.md", recursive=True) + glob.glob(f"{TRASH}/**/*_v37.md", recursive=True):
    trash[book_of(os.path.basename(f))] += 1

print("=== OCR된 교재 universe (카드화 후보) ===")
for b in sorted(ocr):
    inv37 = "✅" if b in v37 else "❌"
    print(f"  [{inv37} v37 {v37.get(b,0):>2}] OCR {ocr[b]:>2}  {b}")

print("\n=== 누락: OCR됐으나 정본(v37)에 카드 없음 ===")
missing = [b for b in sorted(ocr) if b not in v37]
for b in missing:
    loc = []
    if b in old: loc.append(f"02_cards {old[b]}")
    if b in trash: loc.append(f"_trash {trash[b]}")
    print(f"  {b}  (OCR {ocr[b]})" + (f"  ← {' / '.join(loc)}" if loc else "  ← 어디에도 카드 없음"))

print("\n=== 정본(v37)엔 있는데 OCR 폴더엔 없는 책 (비-llamaparse 소스/수기) ===")
for b in sorted(v37):
    if b not in ocr:
        print(f"  v37 {v37[b]:>2}  {b}")

print(f"\n=== 논점재산법 시리즈 확인 ===")
for key in ["논점민법재산법", "논점민법", "논점민소", "기초법리집행법", "재산법"]:
    hits_ocr = [b for b in ocr if key in b]
    hits_v37 = [b for b in v37 if key in b]
    if hits_ocr or hits_v37:
        print(f"  '{key}': OCR={hits_ocr} / v37={hits_v37}")

print(f"\n요약: OCR책 {len(ocr)} / v37카드책 {len(v37)} / 누락 {len(missing)}")
