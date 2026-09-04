"""
Markdown → PDF 변환 스크립트
대상: 형법1 정리노트 2개
출력: H:\내 드라이브\5.기타\정리노트PDF\
"""
import markdown
from xhtml2pdf import pisa
from pathlib import Path
import io
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

CSS_STYLE = """
@page { margin: 20mm 15mm 18mm 15mm; }
body {
    font-family: 'Malgun Gothic', HYGothic, sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #1a1a1a;
}
h1 { font-size: 15pt; border-bottom: 2px solid #333; padding-bottom: 4px; margin-top: 20px; }
h2 { font-size: 12pt; border-bottom: 1px solid #999; padding-bottom: 2px; margin-top: 16px; }
h3 { font-size: 11pt; margin-top: 12px; }
h4 { font-size: 10pt; margin-top: 8px; }
table {
    border-collapse: collapse;
    width: 100%;
    margin: 6px 0;
    font-size: 8.5pt;
}
th {
    background-color: #e0e0e0;
    border: 1px solid #999;
    padding: 3px 6px;
    text-align: left;
}
td {
    border: 1px solid #ccc;
    padding: 3px 6px;
    vertical-align: top;
}
code {
    background-color: #f5f5f5;
    font-family: Consolas, monospace;
    font-size: 8pt;
    padding: 0 3px;
}
pre {
    background-color: #f5f5f5;
    border: 1px solid #ddd;
    padding: 6px;
    font-size: 7.5pt;
    word-wrap: break-word;
}
blockquote {
    border-left: 3px solid #aaa;
    margin: 4px 0;
    padding: 3px 10px;
    color: #444;
    background-color: #fafafa;
}
"""

SOURCES = [
    vp("sync", "1-1_중간", "형법1_서보학_중간_정리노트.md"),
    vp("sync", "1-1_중간", "형법1_중간_압축본.md"),
]
OUT_DIR = Path(vp("5.기타", "정리노트PDF"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "nl2br"])

for src_path in SOURCES:
    src = Path(src_path)
    out_path = OUT_DIR / (src.stem + ".pdf")

    text = src.read_text(encoding="utf-8")
    md.reset()
    body_html = md.convert(text)

    full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{src.stem}</title>
<style>{CSS_STYLE}</style>
</head>
<body>
{body_html}
</body>
</html>"""

    print(f"변환 중: {src.name} → {out_path.name} ...")
    with open(str(out_path), "wb") as f:
        result = pisa.CreatePDF(full_html.encode("utf-8"), dest=f, encoding="utf-8")
    if result.err:
        print(f"  오류 발생: {result.err}")
    else:
        size_kb = out_path.stat().st_size // 1024
        print(f"  완료: {out_path} ({size_kb} KB)")

print("\n모든 파일 변환 완료.")
