"""Round 2: 'Cell N' 라벨 코드 참조 + HF_* 환경변수 의존성."""
import json, re
from pathlib import Path

NB = Path(r"H:\내 드라이브\ocr_extract_v2.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))

code_cells = [(i, "".join(c["source"])) for i, c in enumerate(nb["cells"]) if c["cell_type"] == "code"]
md_cells   = [(i, "".join(c["source"])) for i, c in enumerate(nb["cells"]) if c["cell_type"] == "markdown"]

# 5) 'Cell 1', 'Cell 2', ... 라벨이 코드에서 참조되는지
LABEL_RE = re.compile(r"\bCell\s+\d[a-z]?\b")
ref_hits = []
for i, src in code_cells:
    for m in LABEL_RE.finditer(src):
        line = src[max(0, m.start()-30):m.end()+30].replace("\n", " ")
        ref_hits.append((i, m.group(), line))

print(f"[5] 코드에서 'Cell N' 라벨 참조: {len(ref_hits)}건")
for i, label, ctx in ref_hits[:10]:
    print(f"   - cell {i}: {label!r} | ...{ctx[:80]}...")
if not ref_hits:
    print("[5] 코드 내 'Cell N' 라벨 참조 없음 — 인덱스 밀림 영향 없음")

# 6) HF_* 환경변수 / HF_CACHE 변수 참조
HF_VAR_RE = re.compile(r"\b(HF_HUB_CACHE|HF_HOME|HF_CACHE|TRANSFORMERS_CACHE|HUGGINGFACE_HUB_CACHE|XDG_CACHE_HOME|HF_DATASETS_CACHE)\b")
print("\n[6] HF_* 참조 위치:")
for i, src in code_cells:
    matches = set(HF_VAR_RE.findall(src))
    if matches:
        print(f"   - cell {i}: {sorted(matches)}")
        # 어떤 라인인지
        for ln in src.splitlines():
            if HF_VAR_RE.search(ln):
                print(f"       | {ln.strip()[:110]}")

print("\n=== Round 2 done ===")
