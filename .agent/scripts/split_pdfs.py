"""PDF 분할 스크립트 — 2026-04-24 (라벨 갱신 2026-04-27)
- 형법 COMPACT OX: 책임론 / 미수범 / 공범론 (3분할)
- 송영곤 신민사법 선택형연습 1: 7분할 (민법총칙, 채권법1·2, 인적담보, 물적담보, 물권법, 가족법)

명명규칙: {책ID}_{소제목}_{년도}.pdf
- 인접 책들과 일관 (이인규_*_25, 송영곤_민사법사례연습2_*_23, 논점민법강의_*_26 등)
- 한자/공백/특수문자/다운로드 태그(_3c_r6_2d) 금지
- 원본 stem이 `..._YY` 패턴이면 연도 앞에 라벨 삽입
"""
import re
import sys
from pathlib import Path
from pypdf import PdfReader, PdfWriter

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"H:\내 드라이브")

JOBS = [
    # (source, output_dir, [(label, start_page_1based, end_page_1based_inclusive), ...])
    (
        "2.형사/94.교재/compact형법총론OX_26.pdf",
        "2.형사/94.교재",
        [
            ("책임론", 1, 138),
            ("미수범", 139, 158),
            ("공범론", 159, 251),
        ],
    ),
    (
        "1.민사/94.교재/송영곤_신민사법선택형연습1_26.pdf",
        "1.민사/94.교재",
        [
            ("민법총칙", 1, 155),
            ("채권법1", 156, 317),
            ("채권법2", 318, 477),
            ("인적담보", 478, 509),
            ("물적담보", 510, 589),
            ("물권법", 590, 733),
            ("가족법", 734, 879),
        ],
    ),
]


def split_pdf(src_name: str, out_dir: str, segments):
    src = ROOT / src_name
    out_base = ROOT / out_dir
    out_base.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(src))
    total = len(reader.pages)
    print(f"\n[원본] {src_name}  총 {total}p")
    stem = src.stem
    m = re.match(r"^(.*)_(\d{2})$", stem)
    base, year = (m.group(1), m.group(2)) if m else (stem, None)

    results = []
    for label, start, end in segments:
        writer = PdfWriter()
        for p in range(start - 1, end):
            writer.add_page(reader.pages[p])
        out_name = f"{base}_{label}_{year}.pdf" if year else f"{stem}_{label}.pdf"
        out_path = out_base / out_name
        with open(out_path, "wb") as f:
            writer.write(f)
        size_mb = out_path.stat().st_size / (1024 * 1024)
        n_pages = end - start + 1
        print(f"  [OK] {out_name}  p.{start}-{end} ({n_pages}p, {size_mb:.1f}MB)")
        results.append((out_path, start, end, n_pages, size_mb))
    return results


if __name__ == "__main__":
    all_results = []
    for src, outdir, segs in JOBS:
        res = split_pdf(src, outdir, segs)
        all_results.extend(res)
    print("\n=== 요약 ===")
    print(f"총 {len(all_results)}개 파일 생성")
