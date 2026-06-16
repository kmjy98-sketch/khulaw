"""
정리노트 Markdown → PDF 변환 스크립트
Chrome headless + markdown 사용, 한글(맑은 고딕) 지원

출력 정책:
- PDF는 sync 볼트(`.md` 전용)에 저장하지 않는다.
- 출력 경로: H:/내 드라이브/5.기타/정리노트PDF/{YYYY-MM-DD}/
- 실행 시점의 날짜 폴더를 자동 생성한다.
- 관련 규정: CLAUDE.md § 1-5, .agent/workflows/book-to-notes.md Phase 5
"""
import sys
import os
import subprocess
import tempfile
from datetime import date
import markdown

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_BASE = r"H:\내 드라이브\5.기타\정리노트PDF"

CSS = """
@page {
    size: A4;
    margin: 20mm 18mm 20mm 18mm;
}
@media print {
    body { -webkit-print-color-adjust: exact; }
}
body {
    font-family: "Malgun Gothic", "맑은 고딕", "NanumGothic", sans-serif;
    font-size: 10pt;
    line-height: 1.55;
    color: #1a1a1a;
    word-break: keep-all;
    counter-reset: page;
}
h1 {
    font-size: 18pt;
    border-bottom: 2px solid #333;
    padding-bottom: 6px;
    margin-top: 28px;
    page-break-before: auto;
}
h2 {
    font-size: 14pt;
    border-bottom: 1px solid #999;
    padding-bottom: 4px;
    margin-top: 22px;
    page-break-before: auto;
}
h3 {
    font-size: 12pt;
    margin-top: 16px;
}
h4 { font-size: 11pt; margin-top: 12px; }
table {
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}
th, td {
    border: 1px solid #aaa;
    padding: 5px 8px;
    text-align: left;
    vertical-align: top;
}
th {
    background-color: #f0f0f0;
    font-weight: bold;
}
tr:nth-child(even) { background-color: #fafafa; }
blockquote {
    border-left: 3px solid #4a90d9;
    margin: 10px 0;
    padding: 6px 12px;
    background: #f7f9fc;
    font-size: 9.5pt;
    color: #333;
}
blockquote p { margin: 4px 0; }
blockquote br { line-height: 1.6; }
code {
    background: #f4f4f4;
    padding: 1px 4px;
    border-radius: 3px;
    font-family: "Consolas", monospace;
    font-size: 9pt;
}
pre {
    background: #f4f4f4;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 8.5pt;
    overflow-x: auto;
    page-break-inside: avoid;
}
hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 16px 0;
}
ul, ol { margin: 6px 0; padding-left: 24px; }
li { margin: 2px 0; }
strong { color: #111; }
a { color: #2563eb; text-decoration: none; }

/* 각주 */
.footnote-ref { font-size: 8pt; vertical-align: super; }
.footnotes {
    margin-top: 30px;
    border-top: 1px solid #ccc;
    padding-top: 10px;
    font-size: 8.5pt;
    color: #555;
}
.footnotes ol { padding-left: 20px; }
.footnotes li { margin: 3px 0; }

/* 구분자: 중간/기말 파트 구분 */
.part-divider {
    page-break-before: always;
    text-align: center;
    font-size: 20pt;
    font-weight: bold;
    padding: 60px 0 20px 0;
    color: #333;
    border-bottom: 3px solid #333;
    margin-bottom: 20px;
}

/* HTML comment (페이지 마커) 숨기기 */
.comment { display: none; }
"""


def read_md(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # YAML frontmatter 제거
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:].lstrip("\n")
    return text


def md_to_html(md_text):
    extensions = [
        "tables",
        "footnotes",
        "fenced_code",
        "toc",
        "sane_lists",
        "smarty",
        "nl2br",
    ]
    extension_configs = {
        "footnotes": {"BACKLINK_TEXT": "↩"},
    }
    return markdown.markdown(
        md_text,
        extensions=extensions,
        extension_configs=extension_configs,
    )


def build_combined_html(title, parts):
    """
    parts: list of (part_title, md_file_path)
    """
    body_parts = []
    for i, (part_title, md_path) in enumerate(parts):
        md_text = read_md(md_path)
        html_content = md_to_html(md_text)
        if i > 0:
            body_parts.append(
                f'<div class="part-divider">{part_title}</div>'
            )
        else:
            body_parts.append(
                f'<div class="part-divider" style="page-break-before:avoid;">{part_title}</div>'
            )
        body_parts.append(html_content)

    body = "\n".join(body_parts)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>"""


def generate_pdf(html_str, output_path):
    # HTML을 임시 파일에 저장 후 Chrome headless로 PDF 변환
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(html_str)
        tmp_path = tmp.name

    try:
        cmd = [
            CHROME,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            f"--print-to-pdf={output_path}",
            "--print-to-pdf-no-header",
            "--run-all-compositor-stages-before-draw",
            tmp_path,
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"  !! Chrome 오류: {result.stderr[:300]}")
            return False

        size_kb = os.path.getsize(output_path) / 1024
        print(f"  -> {output_path} ({size_kb:.0f} KB)")
        return True
    finally:
        os.unlink(tmp_path)


def main():
    base = os.path.dirname(os.path.abspath(__file__))

    # 출력 디렉터리: 5.기타/정리노트PDF/{오늘 날짜}/
    # sync 볼트는 .md 전용으로 유지 (CLAUDE.md § 1-5)
    date_dir = date.today().strftime("%Y-%m-%d")
    output_dir = os.path.join(OUTPUT_BASE, date_dir)
    os.makedirs(output_dir, exist_ok=True)

    tasks = [
        {
            "title": "민법1 (강혜림) 정리노트",
            "output": os.path.join(output_dir, "민법1_강혜림_정리노트.pdf"),
            "parts": [
                ("중간고사 범위", os.path.join(base, "1-1_중간", "민법1_강혜림_중간_정리노트.md")),
                ("기말고사 범위", os.path.join(base, "1-1_기말", "민법1_강혜림_기말_정리노트.md")),
            ],
        },
        {
            "title": "민법3 (전경운) 정리노트",
            "output": os.path.join(output_dir, "민법3_전경운_정리노트.pdf"),
            "parts": [
                ("중간고사 범위", os.path.join(base, "1-1_중간", "민법3_전경운_중간_정리노트.md")),
                ("기말고사 범위", os.path.join(base, "1-1_기말", "민법3_전경운_기말_정리노트.md")),
            ],
        },
        {
            "title": "민법1 압축본",
            "output": os.path.join(output_dir, "민법1_압축본.pdf"),
            "parts": [
                ("중간고사 범위", os.path.join(base, "1-1_중간", "민법1_중간_압축본.md")),
                ("기말고사 범위", os.path.join(base, "1-1_기말", "민법1_기말_압축본.md")),
            ],
        },
        {
            "title": "민법3 압축본",
            "output": os.path.join(output_dir, "민법3_압축본.pdf"),
            "parts": [
                ("중간고사 범위", os.path.join(base, "1-1_중간", "민법3_중간_압축본.md")),
                ("기말고사 범위", os.path.join(base, "1-1_기말", "민법3_기말_압축본.md")),
            ],
        },
    ]

    # 커맨드 라인에서 특정 과목만 지정 가능: python md_to_pdf.py 민1 / 민3 / all
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    for task in tasks:
        if target != "all" and target not in task["title"]:
            continue
        print(f"[생성] {task['title']}")
        for pt, pp in task["parts"]:
            if not os.path.exists(pp):
                print(f"  !! 파일 없음: {pp}")
                return
            print(f"  + {pt}: {pp}")
        html = build_combined_html(task["title"], task["parts"])
        generate_pdf(html, task["output"])

    print("\n완료.")


if __name__ == "__main__":
    main()
