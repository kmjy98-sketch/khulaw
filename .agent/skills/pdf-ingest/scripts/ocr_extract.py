#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR-based PDF extraction (스캔본 PDF 전용)
- pymupdf로 페이지 렌더링 → easyocr로 한국어 OCR
- 바운딩박스 기반 레이아웃 분석: 표 구조 자동 탐지 → 마크다운 표 생성
- 페이지 경계 문맥 복원 (종결기호 없이 끝나는 행 + 조사로 시작하는 다음 페이지)
- 기존 ingest.py 출력 포맷과 호환 (chunks_index.json + chunk md 파일)

사용법:
  python ocr_extract.py --pdf "PDF경로" --out "출력디렉토리" [--chunk-size 30] [--dpi 200] [--start 1]
"""
import argparse, json, sys, time, re
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── 레이아웃 분석 ──────────────────────────────────────────────

_SENT_END = re.compile(r'[.!?）\]】」』다함음됨임없있]\s*$')
_CONN_START = re.compile(r'^[의를이가은는에서도과와로으부터까지만도]')

def _bbox_xyxy(box):
    """EasyOCR 4-corner box → (x1, y1, x2, y2)"""
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return min(xs), min(ys), max(xs), max(ys)


def _group_rows(results, row_gap=18):
    """Y 중심값 기준으로 텍스트 박스를 행으로 묶는다."""
    items = []
    for box, text, conf in results:
        if conf < 0.3 or not text.strip():
            continue
        x1, y1, x2, y2 = _bbox_xyxy(box)
        cy = (y1 + y2) / 2
        items.append((cy, x1, x2, text.strip()))
    items.sort(key=lambda t: t[0])

    rows: list[list] = []
    for item in items:
        if rows and item[0] - rows[-1][-1][0] < row_gap:
            rows[-1].append(item)
        else:
            rows.append([item])
    return rows


def _col_anchors(rows, tol=40, min_freq=2):
    """여러 행에 걸쳐 반복되는 X 좌표 → 컬럼 앵커 목록."""
    from collections import Counter
    x_counts: Counter = Counter()
    for row in rows:
        seen = set()
        for cy, x1, x2, _ in row:
            bucket = round(x1 / tol) * tol
            if bucket not in seen:
                x_counts[bucket] += 1
                seen.add(bucket)
    return sorted(x for x, cnt in x_counts.items() if cnt >= min_freq)


def _is_table(rows, min_cols=2, min_rows=2):
    """연속된 행들이 표 구조인지 판단."""
    if len(rows) < min_rows:
        return False
    anchors = _col_anchors(rows)
    return len(anchors) >= min_cols


def _rows_to_md_table(rows):
    """행 목록 → 마크다운 표 문자열."""
    anchors = _col_anchors(rows)
    n_cols = max(len(anchors), 2)

    def assign_col(x1):
        best = min(range(len(anchors)), key=lambda i: abs(anchors[i] - x1))
        return best

    table_rows = []
    for row in rows:
        cells = [""] * n_cols
        for cy, x1, x2, text in sorted(row, key=lambda t: t[1]):
            col = assign_col(x1)
            cells[col] = (cells[col] + " " + text).strip() if cells[col] else text
        table_rows.append(cells)

    if not table_rows:
        return ""

    sep = ["---"] * n_cols
    lines = ["| " + " | ".join(table_rows[0]) + " |",
             "| " + " | ".join(sep) + " |"]
    for row in table_rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _layout_to_markdown(results, table_run=3):
    """
    EasyOCR detail=1 결과 → 마크다운 문자열.
    연속 table_run개 이상의 다중 컬럼 행 → 마크다운 표.
    나머지 → 일반 텍스트 (줄 단위 병합).
    """
    if not results:
        return ""

    rows = _group_rows(results)
    segments: list[str] = []
    i = 0

    while i < len(rows):
        # 표 구간 탐지: 앞으로 table_run개 행이 모두 다중 컬럼이면 표로 간주
        j = i
        while j < len(rows) and len(rows[j]) >= 2:
            j += 1
        run = j - i

        if run >= table_run:
            table_block = rows[i:j]
            if _is_table(table_block):
                segments.append(_rows_to_md_table(table_block))
                i = j
                continue

        # 일반 텍스트: 행 내 박스들을 X 순으로 이어 붙임
        line_parts = [text for cy, x1, x2, text in sorted(rows[i], key=lambda t: t[1])]
        segments.append(" ".join(line_parts))
        i += 1

    return "\n".join(segments)


def _repair_page_boundaries(chunk_text: str) -> str:
    """
    --- Page N --- 마커 앞뒤의 문맥 끊김 복원.
    이전 줄이 종결기호 없이 끝나고 다음 줄이 조사/어미로 시작하면 공백으로 연결.
    """
    PAGE_RE = re.compile(r'\n\n--- Page (\d+) ---\n')
    parts = PAGE_RE.split(chunk_text)
    # parts: [text0, pagenum1, text1, pagenum2, text2, ...]

    if len(parts) <= 1:
        return chunk_text

    out = [parts[0]]
    idx = 1
    while idx < len(parts):
        page_num = parts[idx]
        page_text = parts[idx + 1] if idx + 1 < len(parts) else ""
        idx += 2

        prev_last = out[-1].rstrip().split("\n")[-1] if out[-1].strip() else ""
        next_first = page_text.lstrip().split("\n")[0] if page_text.strip() else ""

        if (prev_last
                and next_first
                and not _SENT_END.search(prev_last)
                and _CONN_START.match(next_first)
                and not next_first.startswith(("#", "-", ">", "|"))):
            # 마커 제거하고 공백으로 연결
            out[-1] = out[-1].rstrip() + page_text
        else:
            out.append(f"\n\n--- Page {page_num} ---\n")
            out.append(page_text)

    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--chunk-size", type=int, default=30)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--start", type=int, default=1, help="시작 페이지 (1-base)")
    ap.add_argument("--end", type=int, default=0, help="종료 페이지 (0=마지막)")
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    chunk_size = args.chunk_size

    print(f"[OCR Extract] {pdf_path.name}")
    print(f"  out: {out_dir}")
    print(f"  chunk_size: {chunk_size} dpi: {args.dpi}")

    print("\n[1] easyocr Reader 로드...")
    t0 = time.time()
    import easyocr
    reader = easyocr.Reader(['ko', 'en'], gpu=False, verbose=False)
    print(f"  loaded in {time.time()-t0:.1f}s")

    print(f"\n[2] PDF 열기")
    import fitz
    doc = fitz.open(str(pdf_path))
    total = len(doc)
    print(f"  pages: {total}")

    start_p = max(1, args.start)
    end_p = total if args.end <= 0 else min(total, args.end)

    # chunks_index.json 로드/생성
    index_path = out_dir / "chunks_index.json"
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            if index.get("chunk_size") != chunk_size:
                index = {"created": datetime.now().isoformat(), "chunk_size": chunk_size, "sources": [], "chunks": []}
        except:
            index = {"created": datetime.now().isoformat(), "chunk_size": chunk_size, "sources": [], "chunks": []}
    else:
        index = {"created": datetime.now().isoformat(), "chunk_size": chunk_size, "sources": [], "chunks": []}

    # 동일 source 있으면 chunks만 갱신
    base_stem = pdf_path.stem
    src_entry = next((s for s in index["sources"] if s["file"] == pdf_path.name), None)
    if not src_entry:
        src_entry = {"file": pdf_path.name, "pages": total, "chunks": [], "source_title": base_stem, "ascii_alias": None}
        index["sources"].append(src_entry)
    else:
        src_entry["pages"] = total
        src_entry["chunks"] = []

    # 기존 같은 source의 chunks 제거
    index["chunks"] = [c for c in index["chunks"] if c.get("source") != pdf_path.name]

    print(f"\n[3] OCR 시작 (pages {start_p}~{end_p})")
    t_total = time.time()

    # chunk 단위로 처리
    for chunk_start in range((start_p - 1) // chunk_size * chunk_size, end_p, chunk_size):
        c_first = chunk_start + 1
        c_last = min(chunk_start + chunk_size, total)
        if c_last < start_p:
            continue
        chunk_name = f"{base_stem}_p{c_first:03d}-{c_last:03d}.md"
        chunk_path = out_dir / chunk_name

        page_blocks = []
        t_chunk = time.time()
        for pno in range(c_first - 1, c_last):
            if pno + 1 < start_p or pno + 1 > end_p:
                continue
            page = doc[pno]
            pix = page.get_pixmap(dpi=args.dpi)
            img_bytes = pix.tobytes("png")
            try:
                results = reader.readtext(img_bytes, detail=1, paragraph=False)
            except Exception as e:
                print(f"  [page {pno+1}] OCR error: {e}")
                results = []
            text = _layout_to_markdown(results)
            page_blocks.append(f"--- Page {pno+1} ---\n{text}")
            elapsed_p = time.time() - t_chunk
            print(f"  page {pno+1}/{end_p} ({len(text)}c) avg {elapsed_p/(pno-c_first+2):.1f}s/p", flush=True)

        chunk_text = _repair_page_boundaries("\n\n".join(page_blocks))
        chunk_path.write_text(chunk_text, encoding="utf-8")

        # keywords
        articles = list(set(re.findall(r'제\d+조(?:의\d+)?', chunk_text)))[:20]
        chunks_info = {
            "id": f"{base_stem}_p{c_first}-{c_last}",
            "source": pdf_path.name,
            "source_title": base_stem,
            "ascii_alias": None,
            "pages": f"{c_first}-{c_last}",
            "file": chunk_name,
            "size": len(chunk_text),
            "keywords": articles,
        }
        index["chunks"].append(chunks_info)
        src_entry["chunks"].append(chunk_name)

        # incremental save
        index["last_updated"] = datetime.now().isoformat()
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  → {chunk_name} ({len(chunk_text):,}c, chunk {time.time()-t_chunk:.0f}s, total {(time.time()-t_total)/60:.1f}min)", flush=True)

    print(f"\n완료 ({(time.time()-t_total)/60:.1f}min)")

if __name__ == "__main__":
    main()
