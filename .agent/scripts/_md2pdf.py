# -*- coding: utf-8 -*-
"""_md2pdf.py — 마크다운 → A4 PDF (한글 Malgun Gothic). reportlab Platypus 엔진. 일회성 유틸(#42).
지원: # 제목 / > 안내 / ## ### 헤더 / - 불릿(2단) / **볼드** / --- 구분선. 표 미사용(찌라시 전제)."""
import sys, io, os, re, html as _html
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont("Malgun", "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont("MalgunBd", "C:/Windows/Fonts/malgunbd.ttf"))
pdfmetrics.registerFontFamily("Malgun", normal="Malgun", bold="MalgunBd",
                              italic="Malgun", boldItalic="MalgunBd")

DARK = HexColor("#111111")
GRAY = HexColor("#555555")
LINE = HexColor("#888888")

S = {
    "title": ParagraphStyle("title", fontName="MalgunBd", fontSize=15, leading=18,
                            spaceAfter=4, textColor=DARK),
    "note": ParagraphStyle("note", fontName="Malgun", fontSize=8.3, leading=11,
                           spaceAfter=6, textColor=GRAY),
    "h2": ParagraphStyle("h2", fontName="MalgunBd", fontSize=10.5, leading=13,
                         spaceBefore=8, spaceAfter=1, textColor=DARK),
    "h3": ParagraphStyle("h3", fontName="MalgunBd", fontSize=9.5, leading=12,
                         spaceBefore=5, spaceAfter=2, textColor=DARK),
    "body": ParagraphStyle("body", fontName="Malgun", fontSize=9.2, leading=12.4,
                           spaceAfter=2, textColor=DARK),
}


def bullet_style(level):
    li = 13 + level * 12
    return ParagraphStyle("b%d" % level, fontName="Malgun", fontSize=9.2, leading=12.4,
                          spaceAfter=2, textColor=DARK, leftIndent=li, firstLineIndent=-11)


def inline(s):
    s = _html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return s


def convert(md_path, pdf_path):
    text = io.open(md_path, encoding="utf-8").read()
    flow = []
    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            flow.append(Spacer(1, 3)); continue
        if line.startswith("# "):
            flow.append(Paragraph(inline(line[2:]), S["title"]))
        elif line.startswith("## "):
            flow.append(Paragraph(inline(line[3:]), S["h2"]))
            flow.append(HRFlowable(width="100%", thickness=0.5, color=LINE,
                                   spaceBefore=1, spaceAfter=3))
        elif line.startswith("### "):
            flow.append(Paragraph(inline(line[4:]), S["h3"]))
        elif line.startswith(">"):
            flow.append(Paragraph(inline(line.lstrip("> ").rstrip()), S["note"]))
        elif line.lstrip().startswith("- ") or line.lstrip().startswith("* "):
            stripped = line.lstrip(" ")
            lvl = min((len(line) - len(stripped)) // 2, 2)
            flow.append(Paragraph("&bull;&nbsp;" + inline(stripped[2:]), bullet_style(lvl)))
        elif set(line.strip()) <= set("-=*") and len(line.strip()) >= 3:
            flow.append(HRFlowable(width="100%", thickness=0.5, color=LINE,
                                   spaceBefore=4, spaceAfter=4))
        else:
            flow.append(Paragraph(inline(line), S["body"]))
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=1.3 * cm, rightMargin=1.3 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm, title=os.path.basename(pdf_path))
    doc.build(flow)
    return True


if __name__ == "__main__":
    for pair in sys.argv[1:]:
        src, dst = pair.split("::")
        try:
            convert(src, dst)
            sz = os.path.getsize(dst) / 1024
            print("OK   %.1f KB  %s" % (sz, dst))
        except Exception as e:
            print("ERR ", dst, "->", repr(e))
