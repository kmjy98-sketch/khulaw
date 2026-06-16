"""Round 1: JSON 무결성 + 추가 셀 ast.parse."""
import json, ast
from pathlib import Path

NB = Path(r"H:\내 드라이브\ocr_extract_v2.ipynb")

# 1) JSON 무결성
with NB.open("r", encoding="utf-8") as f:
    nb = json.load(f)

assert nb.get("nbformat") == 4, f"nbformat != 4: {nb.get('nbformat')}"
assert "cells" in nb and isinstance(nb["cells"], list)
n = len(nb["cells"])
print(f"[1] JSON load OK / nbformat={nb['nbformat']}.{nb.get('nbformat_minor')} / cells={n}")

# nbformat 라이브러리 검증 (있으면)
try:
    import nbformat
    nb2 = nbformat.reads(NB.read_text(encoding="utf-8"), as_version=4)
    nbformat.validate(nb2)
    print("[1] nbformat.validate() OK")
except ImportError:
    print("[1] nbformat 미설치 — json 검증으로 대체")
except Exception as e:
    print(f"[1] nbformat.validate 실패: {e}")
    raise

# 셀별 필수 필드
for i, c in enumerate(nb["cells"]):
    assert c["cell_type"] in ("code", "markdown"), f"cell {i} type"
    assert isinstance(c["source"], list), f"cell {i} source not list"
    if c["cell_type"] == "code":
        assert "outputs" in c, f"cell {i} no outputs"
        assert "execution_count" in c, f"cell {i} no execution_count"
print("[1] 모든 셀 필수 필드 OK")

# 2) Cell 8(0c), Cell 18(시드 백업) ast.parse
def src_of(idx):
    return "".join(nb["cells"][idx]["source"])

for label, idx in [("Cell 0c (idx 8)", 8), ("Cell 5 (idx 18)", 18)]:
    src = src_of(idx)
    try:
        tree = ast.parse(src)
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        print(f"[2] {label} parse OK / 정의된 함수: {funcs or '(없음)'}")
    except SyntaxError as e:
        print(f"[2] {label} SyntaxError: {e}")
        raise

print("\n=== Round 1 PASS ===")
