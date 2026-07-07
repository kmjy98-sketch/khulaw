"""
추출한 PPT에서 사례형 문제 슬라이드만 추려 보고서 작성
"""
import json, re
from pathlib import Path

RAW = Path(r"H:\내 드라이브\9.작업중/클로드\_헌법_PPT_추출_raw.json")
OUT = Path(r"H:\내 드라이브\9.작업중/클로드\_헌법_PPT_추출_요약.md")

# 강한 신호 = 사례형 가능성 높음
STRONG = ["[사례]", "[문제]", "사례 ", "변호사시험", "변시 ", "사실관계",
          "검토하시오", "논하시오", "다음 사례", "다음 사실관계",
          "갑은 ", "갑(", "을은 ", "을(", "甲은", "甲(",
          "기출", "모의시험"]

# 회·문번호 패턴
PATS = [
    re.compile(r"제?\s*(\d+)\s*회\s*변호사시험\s*제?\s*(\d+)\s*문"),
    re.compile(r"변시\s*(\d+)\s*회\s*(\d+)\s*문"),
    re.compile(r"(\d{4})\s*년도?\s*제?\s*(\d+)\s*차\s*변호사시험\s*모의시험"),
    re.compile(r"(\d{1,2})\s*회\s*(\d+)\s*문"),
    re.compile(r"제?\s*(\d+)\s*회\s*변호사시험"),
    re.compile(r"\[?사례\s*(\d+)\]?"),
    re.compile(r"\[?Case\s*(\d+)\]?", re.I),
    re.compile(r"\[?문제\s*(\d+)\]?"),
]

def find_meta(text):
    found = []
    for pat in PATS:
        for m in pat.finditer(text):
            found.append({"pattern": pat.pattern, "match": m.group(0), "groups": list(m.groups())})
    return found

def is_case(text, hits):
    """사례형 슬라이드 여부 판단"""
    strong_hit = [s for s in STRONG if s in text]
    # 사실관계+질문 패턴: 한 슬라이드 안에 인물(갑/을/甲/乙)+행위 묘사 + 검토/논/위헌 등
    has_actor = any(k in text for k in ["갑은", "갑(", "을은", "을(", "甲은", "甲(", "乙은", "乙("])
    has_question = any(k in text for k in ["검토하시오", "논하시오", "위헌인가", "합헌인가",
                                              "침해되는가", "헌법소원", "위헌 여부",
                                              "심판청구", "어떤 권리"])
    return strong_hit, has_actor, has_question

def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    lines = ["# 헌법 교수님 PPT — 사례형 문제 후보 추출 (raw)\n"]
    lines.append("> 자동 추출 결과. 회·문번호는 PPT 본문에 명시된 것만 표기.\n")

    total_cases = 0
    for fname, data in raw.items():
        if "error" in data:
            lines.append(f"\n## ERROR: {fname}\n- {data['error']}\n")
            continue
        slide_count = data["slide_count"]
        case_slides = []
        for s in data["slides"]:
            text = s["text"]
            if not text.strip():
                continue
            strong, actor, question = is_case(text, s["hits"])
            score = len(strong) + (2 if actor else 0) + (2 if question else 0)
            if score >= 2:  # 후보 채택 임계값
                meta = find_meta(text)
                case_slides.append({
                    "slide": s["slide"],
                    "score": score,
                    "strong_hits": strong,
                    "actor": actor,
                    "question": question,
                    "meta": meta,
                    "preview": text[:600],
                })
        lines.append(f"\n## {fname}")
        lines.append(f"- 총 슬라이드: {slide_count}")
        lines.append(f"- 사례형 후보: {len(case_slides)}\n")
        total_cases += len(case_slides)
        for c in case_slides:
            lines.append(f"### 슬라이드 {c['slide']} (score={c['score']})")
            if c["strong_hits"]:
                lines.append(f"- 강한 신호: {', '.join(c['strong_hits'])}")
            if c["meta"]:
                lines.append(f"- 회·문번호 후보: {[m['match'] for m in c['meta']]}")
            lines.append(f"- 사실관계 인물: {c['actor']}, 질문 패턴: {c['question']}")
            preview = c["preview"].replace("\n", " / ")
            lines.append(f"- preview: {preview}")
            lines.append("")

    lines.append(f"\n---\n총 사례형 후보 슬라이드: **{total_cases}**")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved: {OUT}")
    print(f"Total case slides: {total_cases}")

if __name__ == "__main__":
    main()
