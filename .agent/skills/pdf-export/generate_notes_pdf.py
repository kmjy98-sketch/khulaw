#!/usr/bin/env python3
"""정리노트 MD → PDF 배치 변환 (playwright + markdown 사용)"""
import sys, argparse, tempfile, markdown
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CSS = """
@page { size: A4; margin: 15mm 12mm; }
body { font-family: "Malgun Gothic", "맑은 고딕", sans-serif; font-size: 10pt; line-height: 1.6; color: #1a1a1a; }
h1 { font-size: 18pt; border-bottom: 2px solid #333; padding-bottom: 4px; margin-top: 20px; }
h2 { font-size: 14pt; border-bottom: 1px solid #666; padding-bottom: 3px; margin-top: 16px; page-break-after: avoid; }
h3 { font-size: 12pt; margin-top: 12px; page-break-after: avoid; }
h4, h5 { font-size: 10.5pt; margin-top: 8px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9pt; }
th, td { border: 1px solid #999; padding: 4px 6px; text-align: left; }
th { background: #e8e8e8; font-weight: bold; }
tr:nth-child(even) { background: #f5f5f5; }
blockquote { border-left: 3px solid #666; padding-left: 10px; margin: 8px 0; color: #444; }
code { font-family: "Consolas", monospace; font-size: 9pt; background: #f0f0f0; padding: 1px 3px; }
pre { background: #f0f0f0; padding: 8px; font-size: 8.5pt; overflow-x: auto; white-space: pre-wrap; }
strong { color: #000; }
.footnote { font-size: 8.5pt; color: #555; border-top: 1px solid #ccc; margin-top: 16px; padding-top: 4px; }
.footnote ol { padding-left: 16px; }
"""


def md_to_html(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "toc", "footnotes", "nl2br"],
    )
    return (
        "<!DOCTYPE html><html><head>"
        '<meta charset="utf-8">'
        f"<style>{CSS}</style>"
        f"</head><body>{html_body}</body></html>"
    )


def convert_one(md_path: Path, pdf_path: Path, page) -> None:
    html = md_to_html(md_path)
    tmp_html = pdf_path.with_suffix(".html")
    try:
        tmp_html.write_text(html, encoding="utf-8")
        page.goto(f"file:///{tmp_html.resolve().as_posix()}")
        page.wait_for_load_state("networkidle")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"},
            print_background=True,
        )
    finally:
        if tmp_html.exists():
            tmp_html.unlink()


def main():
    parser = argparse.ArgumentParser(description="MD → PDF 배치 변환 (playwright)")
    parser.add_argument("--src", required=True, nargs="+", help="소스 .md 파일 또는 폴더")
    parser.add_argument("--out", required=True, help="PDF 출력 폴더")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_files = []
    for s in args.src:
        p = Path(s)
        if p.is_file() and p.suffix == ".md":
            md_files.append(p)
        elif p.is_dir():
            md_files.extend(sorted(p.glob("*.md")))

    if not md_files:
        print("변환 대상 .md 파일이 없습니다.")
        return

    print(f"변환 대상: {len(md_files)}개 → {out_dir}")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page_obj = browser.new_page()
        for md in md_files:
            pdf = out_dir / md.with_suffix(".pdf").name
            try:
                convert_one(md, pdf, page_obj)
                size_kb = pdf.stat().st_size // 1024
                print(f"  OK: {pdf.name} ({size_kb}KB)")
            except Exception as e:
                print(f"  FAIL: {md.name} — {e}")
        browser.close()


if __name__ == "__main__":
    main()
