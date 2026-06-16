"""
헌법 교수님 PPT 텍스트 추출 + 사례형 문제 식별
- input: 3.공법/10.이진_헌법원리1/*.pptx + 7주.pdf
- output: sync/_meta/_헌법_PPT_추출_raw.json
"""
import json
import os
from pathlib import Path
from pptx import Presentation

BASE = Path(r"H:\내 드라이브\3.공법\10.이진_헌법원리1")
OUT = Path(r"H:\내 드라이브\sync\_meta\_헌법_PPT_추출_raw.json")

KEYWORDS = ["사례", "Case", "case", "CASE", "변시", "변호사시험", "기출",
            "사실관계", "검토하시오", "논하시오", "위헌", "침해", "청구",
            "합헌인가", "위헌인가", "처분", "심판", "갑(", "갑은", "을은", "을(",
            "[문제]", "[사례]", "Q.", "Question", "다음 사례", "다음 사실관계",
            "변호사", "모의", "기말", "중간"]

def extract_pptx(p: Path):
    prs = Presentation(str(p))
    slides = []
    for i, slide in enumerate(prs.slides, 1):
        texts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        if run.text.strip():
                            texts.append(run.text.strip())
            # table support
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            texts.append(cell.text.strip())
        full = "\n".join(texts)
        hits = [k for k in KEYWORDS if k in full]
        slides.append({
            "slide": i,
            "text": full,
            "hits": hits,
        })
    return {
        "file": str(p),
        "slide_count": len(prs.slides),
        "slides": slides,
    }

def main():
    pptx_files = sorted([p for p in BASE.glob("*.pptx")])
    print(f"PPTX files: {len(pptx_files)}")
    out = {}
    for p in pptx_files:
        try:
            print(f"  extracting: {p.name}")
            out[p.name] = extract_pptx(p)
        except Exception as e:
            print(f"  ERROR {p.name}: {e}")
            out[p.name] = {"error": str(e)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {OUT}")

if __name__ == "__main__":
    main()
