"""Round 4: Cell 2 실행 후 os.environ에 OCR_* 4건이 의도값으로 들어가는지."""
import json, os
from pathlib import Path

NB = Path(r"H:\내 드라이브\ocr_extract_v2.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))
src = "".join(nb["cells"][2]["source"])

# 격리된 환경에서 실행
test_env = {}
exec(src, {"__builtins__": __builtins__}, test_env)

EXPECTED = {
    "OCR_MAX_RAM_GB": "11",
    "OCR_RECYCLE_EVERY": "1",
    "OCR_SKIP_LARGE": "500",
    "OCR_LARGE_PDF_THRESHOLD": "200",
    "OCR_SMALL_CHUNK": "10",
}

print("=== Cell 2 실행 후 os.environ 상태 ===")
all_ok = True
for k, expect in EXPECTED.items():
    got = os.environ.get(k)
    mark = "✓" if got == expect else "✗"
    if got != expect:
        all_ok = False
    print(f"  {mark} {k:30s} expect={expect:>4s}  got={got}")

# 정수 파싱 가능 여부 (실제 코드가 int(os.environ[k])로 사용)
print("\n=== int 파싱 검증 ===")
for k in EXPECTED:
    v = os.environ.get(k)
    try:
        n = int(v)
        print(f"  ✓ {k} = {n}")
    except (TypeError, ValueError) as e:
        print(f"  ✗ {k} 파싱 실패: {e}")
        all_ok = False

print(f"\n=== Round 4: {'PASS' if all_ok else 'FAIL'} ===")
