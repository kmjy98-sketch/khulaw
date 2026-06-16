"""청크 처리 시간 분석 — progress.json + 산출물 mtime."""
import json, os, re, sys, io
from pathlib import Path
from datetime import datetime
from statistics import mean, median

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OUT = Path(r"H:\내 드라이브\sync\_ocr_extracted")
PROG = Path(r"H:\내 드라이브\.auto-memory\ocr_state\progress.json")
OFFSET = Path(r"H:\내 드라이브\.auto-memory\ocr_state\offset_table.json")

prog = json.loads(PROG.read_text(encoding="utf-8"))
offset = json.loads(OFFSET.read_text(encoding="utf-8"))

records = []
RANGE_RE = re.compile(r"_p(\d{4})-(\d{4})\.md$")
for book_dir in OUT.iterdir():
    if not book_dir.is_dir(): continue
    for f in book_dir.iterdir():
        if not f.name.endswith(".md"): continue
        m = RANGE_RE.search(f.name)
        if not m: continue
        s, e = int(m.group(1)), int(m.group(2))
        records.append({
            "book": book_dir.name, "start": s, "end": e, "pages": e - s + 1,
            "mtime": f.stat().st_mtime, "fname": f.name,
        })
records.sort(key=lambda r: r["mtime"])

RELOAD_TS = datetime(2026, 4, 27, 19, 0).timestamp()
post = [r for r in records if r["mtime"] >= RELOAD_TS]
print(f"전체 산출물: {len(records)} / reload 이후: {len(post)}")
print()

gaps = []
for i in range(1, len(post)):
    dt = post[i]["mtime"] - post[i-1]["mtime"]
    same_book = post[i]["book"] == post[i-1]["book"]
    gaps.append({
        "dt": dt, "pages": post[i]["pages"], "book": post[i]["book"],
        "range": f"{post[i]['start']:>4}-{post[i]['end']:>4}",
        "ts": datetime.fromtimestamp(post[i]["mtime"]).strftime("%H:%M:%S"),
        "same_book": same_book,
    })

# 1) 같은 책 내부 청크 (모델 재로딩 영향 적음)
in_book = [g for g in gaps if g["same_book"]]
# 2) 책 전환 gap (RECYCLE_EVERY=1 모델 재로딩 + 책간 오버헤드)
cross = [g for g in gaps if not g["same_book"]]

print("=== 같은 책 내 연속 청크 (모델 재로딩 X) ===")
if in_book:
    by_size = {}
    for g in in_book:
        by_size.setdefault(g["pages"], []).append(g["dt"])
    for p, lst in sorted(by_size.items()):
        if len(lst) >= 1:
            mn, md, mx = min(lst), median(lst), max(lst)
            avg = mean(lst)
            pph = 3600 / avg * p if avg > 0 else 0
            print(f"  {p:>3}p: n={len(lst):>3} / mean={avg:>5.0f}s / med={md:>5.0f}s / min={mn:>4.0f}s / max={mx:>5.0f}s / 환산={pph:>5.0f}p/h")
print()

print("=== 책 전환 gap (RECYCLE_EVERY=1 → 매 책 모델 재로딩 비용) ===")
if cross:
    dts = [g["dt"] for g in cross]
    pgs = [g["pages"] for g in cross]
    print(f"  n={len(cross)} / mean={mean(dts):.0f}s / med={median(dts):.0f}s / min={min(dts):.0f}s / max={max(dts):.0f}s")
    print(f"  첫 청크 평균 페이지: {mean(pgs):.1f}p")
    # 모델 재로딩 추정 = 책 전환 gap - (첫 청크 페이지 처리 시간 추정 = 같은책 같은 청크크기 평균)
    # 가장 흔한 첫 청크 크기는 50p (LARGE_PDF_THRESHOLD=200 미만 책의 통째 청크)
    # 또는 SMALL_CHUNK=10p
    print()
    print("  책 전환 gap 분포 (큰 순서, top 10):")
    for g in sorted(cross, key=lambda x: -x["dt"])[:10]:
        print(f"   - {g['ts']}  +{g['dt']:>5.0f}s  {g['pages']:>3}p  {g['book'][:55]}")
print()

# 책별 청크 크기 분포 (어떤 책이 SMALL_CHUNK=10p로 쪼개졌나)
print("=== 책별 청크 크기 패턴 ===")
chunks_by_book = {}
for r in post:
    chunks_by_book.setdefault(r["book"], []).append((r["start"], r["end"], r["pages"]))
for book, chs in sorted(chunks_by_book.items(), key=lambda x: x[1][-1][1] if x[1] else 0, reverse=True):
    chs.sort()
    sizes = [c[2] for c in chs]
    total = chs[-1][1] if chs else 0
    book_total = offset.get(book, {}).get("total_pages", "?")
    is_small = any(s == 10 for s in sizes)
    chunk_label = "SMALL=10p" if is_small else f"청크={sizes[0] if sizes else '?'}p"
    print(f"  [{chunk_label:>10}] 처리 {total:>3}/{book_total} | 청크수={len(chs)} | {book[:55]}")
print()

# 시간 gap > 5min (OOM/disconnect 추정)
print("=== gap > 300s 비정상 ===")
big = [g for g in gaps if g["dt"] > 300]
print(f"  count={len(big)}")
for g in big:
    typ = "책전환" if not g["same_book"] else "책내부"
    print(f"   {g['ts']}  +{g['dt']:>5.0f}s [{typ}] {g['pages']:>3}p  {g['book'][:55]}")
