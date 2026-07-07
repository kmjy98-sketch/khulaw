#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""카드(02_cards_v37) vs 마크다운책(01_ocr_llamaparse) 누락/보존율 대조.
일회성 분석 스크립트 (#42). 파일 읽기/쓰기 없이 scandir+카드 1회 read.
"""
import os, re, json, sys

BASE = r"H:\내 드라이브\outputs"
OCR_DIR = os.path.join(BASE, "01_ocr_llamaparse")
CARD_DIR = os.path.join(BASE, "02_cards_v37")

PAGE_RE = re.compile(r"p(\d{1,4})-(\d{1,4})")

def norm_book(name):
    """파일명 → 책 정규화 키."""
    n = name
    n = re.sub(r"\.md$", "", n)
    n = re.sub(r"_v3\d?", "", n)
    n = re.sub(r"_llamaparse", "", n)
    n = re.sub(r"_ocrlog.*", "", n)
    for t in ("기본서", "암기장", "cards", "정리", "교안"):
        n = n.replace("_" + t, "").replace(t, "")
    n = re.sub(r"_?p\d{1,4}-\d{1,4}.*", "", n)  # 페이지 토큰 이후 제거
    n = n.replace("_", "")
    return n.strip().lower()

def card_type(name):
    if "암기장" in name: return "암기장"
    if "기본서" in name: return "기본서"
    return "기타"

def scan(d):
    out = []
    anomalies = []
    for e in os.scandir(d):
        if not e.is_file():
            anomalies.append(("dir/non-file", e.name))
            continue
        if not e.name.endswith(".md"):
            if "ocrlog" not in e.name:
                anomalies.append(("non-md", e.name))
            continue
        m = PAGE_RE.search(e.name)
        if not m:
            anomalies.append(("no-page-range", e.name))
            continue
        s, en = int(m.group(1)), int(m.group(2))
        out.append({
            "name": e.name, "book": norm_book(e.name),
            "start": s, "end": en, "size": e.stat().st_size,
        })
    return out, anomalies

print("[scan] OCR ...", file=sys.stderr)
ocr, ocr_anom = scan(OCR_DIR)
print("[scan] CARD ...", file=sys.stderr)
card, card_anom = scan(CARD_DIR)

# 카드 card 개수(## 헤딩) — 읽기 1회씩
def count_cards(path):
    try:
        with open(path, encoding="utf-8") as f:
            txt = f.read()
        return len(re.findall(r"^##\s+", txt, re.M))
    except Exception as ex:
        return -1

print("[count] cards ## headings ...", file=sys.stderr)
for c in card:
    c["ncards"] = count_cards(os.path.join(CARD_DIR, c["name"]))

# 그룹화
books = {}
for o in ocr:
    b = books.setdefault(o["book"], {"ocr": [], "card": []})
    b["ocr"].append(o)
for c in card:
    b = books.setdefault(c["book"], {"ocr": [], "card": []})
    b["card"].append(c)

def pages(chunk):
    return chunk["end"] - chunk["start"] + 1

report = {"books": [], "totals": {}}
tot_ocr_pages = tot_carded_pages = tot_missing_pages = 0
tot_ocr_books = tot_card_only = 0

lines = []
lines.append("# 카드(02_cards_v37) vs 마크다운책(01_ocr_llamaparse) 누락 대조")
lines.append("")
lines.append(f"생성: 2026-06-21 / OCR책 {len(ocr)}개 청크, v37카드 {len(card)}개 청크\n")

for book in sorted(books):
    g = books[book]
    ocr_ranges = sorted({(o["start"], o["end"]) for o in g["ocr"]})
    card_ranges = sorted({(c["start"], c["end"]) for c in g["card"]})
    card_range_set = set(card_ranges)
    ocr_range_set = set(ocr_ranges)
    missing = [r for r in ocr_ranges if r not in card_range_set]      # 책엔 있고 카드 없음
    card_only = [r for r in card_ranges if r not in ocr_range_set]    # 카드만 있고 책 없음(매칭경고)

    ocr_pages = sum(e - s + 1 for s, e in ocr_ranges)
    carded_pages = sum(e - s + 1 for s, e in ocr_ranges if (s, e) in card_range_set)
    missing_pages = sum(e - s + 1 for s, e in missing)

    ocr_bytes = sum(o["size"] for o in g["ocr"])
    card_bytes = sum(c["size"] for c in g["card"])
    ncards = sum(c["ncards"] for c in g["card"] if c["ncards"] > 0)

    if g["ocr"]:
        tot_ocr_pages += ocr_pages
        tot_carded_pages += carded_pages
        tot_missing_pages += missing_pages
        tot_ocr_books += 1
    if g["card"] and not g["ocr"]:
        tot_card_only += 1

    cov = (carded_pages / ocr_pages * 100) if ocr_pages else 0.0
    report["books"].append({
        "book": book, "ocr_chunks": len(ocr_ranges), "card_chunks": len(card_ranges),
        "ocr_pages": ocr_pages, "carded_pages": carded_pages, "missing_pages": missing_pages,
        "coverage_pct": round(cov, 1), "missing_ranges": missing, "card_only_ranges": card_only,
        "ocr_kb": round(ocr_bytes/1024), "card_kb": round(card_bytes/1024),
        "ncards": ncards,
        "ocr_raw": sorted(o["name"] for o in g["ocr"]),
        "card_raw": sorted(c["name"] for c in g["card"]),
    })

# 정렬: 누락 페이지 많은 순
report["books"].sort(key=lambda b: (-b["missing_pages"], -b["ocr_pages"]))

lines.append("## 책별 청크 커버리지 (누락 많은 순)\n")
lines.append("| 책(정규화) | OCR청크 | 카드청크 | OCR쪽수 | 카드된쪽 | 누락쪽 | 커버리지 | 카드수 |")
lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
for b in report["books"]:
    flag = " ⚠없음" if b["ocr_chunks"] == 0 else ""
    lines.append(f"| {b['book']}{flag} | {b['ocr_chunks']} | {b['card_chunks']} | {b['ocr_pages']} | {b['carded_pages']} | {b['missing_pages']} | {b['coverage_pct']}% | {b['ncards']} |")

lines.append("")
lines.append("## 누락 구간 상세 (책엔 있으나 카드 없음)\n")
for b in report["books"]:
    if b["missing_ranges"]:
        rs = ", ".join(f"p{s:03d}-{e:03d}" for s, e in b["missing_ranges"])
        lines.append(f"- **{b['book']}** ({b['missing_pages']}쪽 누락): {rs}")

lines.append("")
lines.append("## 매칭 경고 (카드만 있고 책 청크 없음 — 책이름 정규화 불일치 가능)\n")
any_co = False
for b in report["books"]:
    if b["card_only_ranges"]:
        any_co = True
        rs = ", ".join(f"p{s:03d}-{e:03d}" for s, e in b["card_only_ranges"])
        lines.append(f"- **{b['book']}**: {rs}  (card_raw 예: {b['card_raw'][:2]})")
if not any_co:
    lines.append("- 없음")

tot_cov = (tot_carded_pages / tot_ocr_pages * 100) if tot_ocr_pages else 0
lines.append("")
lines.append("## 총계\n")
lines.append(f"- OCR책 보유 책 수: {tot_ocr_books}")
lines.append(f"- 카드만 존재(OCR 청크 매칭 안됨) 책 수: {tot_card_only}")
lines.append(f"- 전체 OCR 쪽수: {tot_ocr_pages}")
lines.append(f"- 카드화된 쪽수: {tot_carded_pages}")
lines.append(f"- **누락 쪽수: {tot_missing_pages}** (청크 단위 전체누락)")
lines.append(f"- 전체 청크 커버리지: {tot_cov:.1f}%")

lines.append("")
lines.append("## 이상치(anomalies)\n")
lines.append(f"- OCR dir: {ocr_anom}")
lines.append(f"- CARD dir: {card_anom}")

report["totals"] = {
    "ocr_books": tot_ocr_books, "card_only_books": tot_card_only,
    "ocr_pages": tot_ocr_pages, "carded_pages": tot_carded_pages,
    "missing_pages": tot_missing_pages, "coverage_pct": round(tot_cov, 1),
    "ocr_anom": ocr_anom, "card_anom": card_anom,
}

out_md = r"H:\내 드라이브\9.작업중/클로드\카드vs책_누락대조_2026-06-21.md"
out_json = r"H:\내 드라이브\.agent\state\_card_vs_book_coverage_2026-06-21.json"
with open(out_md, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print("\n".join(lines))
print(f"\n[written] {out_md}\n[written] {out_json}", file=sys.stderr)
