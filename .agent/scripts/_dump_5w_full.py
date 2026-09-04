import json, re, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402
RAW = Path(vp("sync", "_meta", "_헌법_PPT_추출_raw.json"))
raw = json.loads(RAW.read_text(encoding="utf-8"))
key = [k for k in raw if "5주" in k][0]
data = raw[key]

def normalize(text):
    return re.sub(r"\s+", " ", text)

for s in data["slides"]:
    if s["slide"] in (22, 23, 24, 25, 26, 27, 38, 39, 56, 57, 58, 59, 60):
        print(f"\n=== 5주 슬라이드 {s['slide']} ===")
        print(normalize(s["text"]))

# 6주도 사례 후보 더 있을지: 슬라이드별 actor 단어 검사
print("\n\n=== 6주 PPT 인물지칭(甲/乙/갑/을) 슬라이드 ===")
key6 = [k for k in raw if "6주" in k][0]
for s in raw[key6]["slides"]:
    text = normalize(s["text"])
    if any(w in text for w in ["甲은", "甲(", "乙은", "乙(", "甲이", "사례풀이", "변호사시험", "변시", "모의시험"]):
        print(f"\n[6주 슬라이드 {s['slide']}]")
        print(text[:500])
