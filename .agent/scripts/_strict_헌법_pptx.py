"""
엄격한 사례형 문제만 추출 - 변시/모의시험 명시 또는 [사례] 명시
"""
import json, re
from pathlib import Path

RAW = Path(r"H:\내 드라이브\sync\_meta\_헌법_PPT_추출_raw.json")

# 진짜 사례형 강한 신호
HARD_PATTERNS = [
    re.compile(r"제?\s*\d+\s*회\s*변호사시험"),
    re.compile(r"\d{4}\s*년?\s*변호사시험\s*\d+\s*회"),
    re.compile(r"\d{4}\s*년도?\s*제?\s*\d+\s*차\s*변호사\s*모의?시험"),
    re.compile(r"변시\s*\d+\s*회"),
    re.compile(r"\[사례\s*\d*\]"),
    re.compile(r"\[문제\]"),
    re.compile(r"<\s*사례\s*>"),
    re.compile(r"사례풀이"),
    re.compile(r"기말고사"),
    re.compile(r"중간고사"),
    re.compile(r"진급시험"),
]

def main():
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    print("=" * 80)
    print("STRICT CASE EXTRACTION - 변시/모의/[사례] 명시 슬라이드만")
    print("=" * 80)

    total = 0
    for fname, data in raw.items():
        if "error" in data:
            continue
        hits_in_file = []
        for s in data["slides"]:
            text = s["text"]
            if not text.strip():
                continue
            matches = []
            for pat in HARD_PATTERNS:
                for m in pat.finditer(text):
                    matches.append(m.group(0))
            if matches:
                hits_in_file.append({"slide": s["slide"], "matches": matches, "text": text})
        if hits_in_file:
            print(f"\n=== {fname} (총 슬라이드 {data['slide_count']}) ===")
            print(f"  hard hits: {len(hits_in_file)}")
            for h in hits_in_file:
                print(f"\n  [슬라이드 {h['slide']}] matches: {h['matches']}")
                # 첫 200자 보여주기
                preview = h['text'][:300].replace('\n', ' / ')
                print(f"    text(0-300): {preview}")
                total += 1
    print(f"\n\n총 강한 신호 슬라이드: {total}")

if __name__ == "__main__":
    main()
