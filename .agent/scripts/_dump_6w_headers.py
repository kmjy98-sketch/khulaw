import json, re, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402
RAW = Path(vp("sync", "_meta", "_헌법_PPT_추출_raw.json"))
raw = json.loads(RAW.read_text(encoding="utf-8"))

def normalize(text):
    return re.sub(r"\s+", " ", text)

# 모든 PPT의 모든 슬라이드 첫 60자 + 변시/문/사례 키워드
print("=" * 80)
print("ALL PPTX SLIDE HEADERS — 사례/문/변시 키워드 강조")
print("=" * 80)

for fname, data in raw.items():
    if "error" in data:
        continue
    print(f"\n## {fname} ({data['slide_count']} slides)")
    for s in data["slides"]:
        text = normalize(s["text"])
        head = text[:80] if text else "(빈 슬라이드)"
        # 사례/변시/문 흔적
        flags = []
        if re.search(r"변시|변호사시험|모의시험|사례풀이|사례문제|<\s*사례|\[사례", text):
            flags.append("CASE")
        if re.search(r"선택형|객관식|기출.*문제|문\s*\d+", text):
            flags.append("MCQ")
        flag_str = f" [{','.join(flags)}]" if flags else ""
        print(f"  {s['slide']:3d}{flag_str}: {head}")
