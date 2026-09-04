"""
5주 PPT의 사례풀이 부분 + 모든 PPT의 53~63 슬라이드 강한 신호 재검토
줄바꿈 무시한 매칭으로 회·문번호 추출
"""
import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pathlib import Path
RAW = Path(r"H:\내 드라이브\9.작업중/클로드\_헌법_PPT_추출_raw.json")

def normalize(text):
    """모든 공백/개행을 단일 공백으로"""
    return re.sub(r"\s+", " ", text)

PATS = [
    re.compile(r"(\d{4})\s*년\s*제?\s*(\d+)\s*회\s*변[호시]사?시험"),
    re.compile(r"제?\s*(\d+)\s*회\s*변호사시험"),
    re.compile(r"(\d{4})\s*년도?\s*제?\s*(\d+)\s*차\s*변호사\s*모의?시험"),
    re.compile(r"변시\s*(\d+)\s*회"),
    re.compile(r"\[?사례\s*(\d+)\]?"),
    re.compile(r"<\s*사례\s*\d*\s*>"),
    re.compile(r"사례풀이"),
    re.compile(r"답안예시"),
    re.compile(r"기말고사"),
    re.compile(r"중간고사"),
    re.compile(r"진급시험"),
    re.compile(r"\(\s*문제\s*\)"),
    re.compile(r"<\s*문제\s*>"),
    re.compile(r"\[\s*문제\s*\]"),
]

def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    for fname, data in raw.items():
        if "error" in data:
            continue
        for s in data["slides"]:
            text = normalize(s["text"])
            if not text.strip():
                continue
            matches = []
            for pat in PATS:
                for m in pat.finditer(text):
                    matches.append(m.group(0))
            if matches:
                print(f"\n[{fname}] 슬라이드 {s['slide']}")
                print(f"  matches: {matches}")
                print(f"  text(400): {text[:400]}")

if __name__ == "__main__":
    main()
