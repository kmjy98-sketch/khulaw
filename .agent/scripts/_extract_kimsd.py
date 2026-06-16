"""김성돈 형법총론 - 범죄요소·적용범위 PDF 직접 텍스트 추출.

PyMuPDF native text-layer extraction.
출력: H:/내 드라이브/sync/_교재원문/형법/김성돈_형법총론/_재추출/
"""

from __future__ import annotations

import re
from pathlib import Path

import fitz  # PyMuPDF


ROOT = Path(r"H:\내 드라이브")
PDF_DIR = ROOT / "2.형사" / "40.김성돈_형법총론" / "교재"
OUT_DIR = ROOT / "sync" / "_교재원문" / "형법" / "김성돈_형법총론" / "_재추출"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_pdf_text(pdf_path: Path, out_md: Path, title: str, sub_book: str) -> dict:
    """PDF → markdown with per-page markers."""
    doc = fitz.open(pdf_path)
    n_pages = len(doc)

    body_lines: list[str] = []
    page_chars: list[int] = []

    for i in range(n_pages):
        page = doc[i]
        # blocks 순서 보존 모드
        text = page.get_text("text", sort=True)
        text = text.strip()
        page_chars.append(len(text))
        body_lines.append(f"\n<!-- p.{i + 1} -->\n")
        body_lines.append(text)
        body_lines.append("")

    doc.close()

    body = "\n".join(body_lines)
    total_chars = sum(page_chars)

    front = (
        "---\n"
        f"tags: [교재원문, 형법, 김성돈_형법총론, {sub_book}]\n"
        "교재: 김성돈 《형법총론》\n"
        "판: 25\n"
        "과목: 형법\n"
        f"서브책자: {sub_book}\n"
        f"포함_페이지: 1-{n_pages}\n"
        f"원본PDF: {pdf_path.name}\n"
        "추출엔진: PyMuPDF-1.26.7 (native text-layer)\n"
        "추출일: 2026-04-30\n"
        "추출방식: 페이지 단위 raw text + p.N 마커\n"
        "---\n"
    )

    full = front + f"\n# {title}\n\n## 0. 추출 메타\n\n" + (
        f"- 총 페이지: {n_pages}\n"
        f"- 총 글자수: {total_chars:,}\n"
        f"- 페이지별 글자수 평균: {total_chars / max(1, n_pages):.0f}\n"
        f"- 추출엔진: PyMuPDF native text-layer\n\n"
        "---\n"
    ) + body

    out_md.write_text(full, encoding="utf-8")

    return {
        "n_pages": n_pages,
        "total_chars": total_chars,
        "out": str(out_md),
    }


def main() -> None:
    targets = [
        (
            PDF_DIR / "김성돈_형법총론_범죄요소_25.pdf",
            OUT_DIR / "김성돈_형법총론_범죄요소_25_PyMuPDF재추출.md",
            "김성돈 《형법총론》 — 범죄요소 (PyMuPDF 재추출)",
            "범죄요소",
        ),
        (
            PDF_DIR / "김성돈_형법총론_적용범위_25.pdf",
            OUT_DIR / "김성돈_형법총론_적용범위_25_PyMuPDF재추출.md",
            "김성돈 《형법총론》 — 적용범위 (PyMuPDF 재추출)",
            "적용범위",
        ),
    ]

    for pdf, out_md, title, sub_book in targets:
        if not pdf.exists():
            print(f"[MISS] {pdf}")
            continue
        info = extract_pdf_text(pdf, out_md, title, sub_book)
        print(
            f"[OK] {pdf.name}: pages={info['n_pages']} chars={info['total_chars']:,} → {info['out']}"
        )


if __name__ == "__main__":
    main()
