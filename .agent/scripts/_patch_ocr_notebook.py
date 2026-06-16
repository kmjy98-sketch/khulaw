"""Cell 12(=Cell 2 본체) 첫 부분에 0b 의존 변수 fallback 추가."""
import json, os, sys, io, shutil, ast
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

NB = Path(r"H:\내 드라이브\ocr_extract_v2.ipynb")
ts = datetime.now().strftime("%Y-%m-%d_%H%M")
BACKUP = Path(r"H:\내 드라이브\5.기타") / f"ocr_extract_v2.bak_{ts}_cell2_fallback.ipynb"
shutil.copy2(NB, BACKUP)
print(f"[backup] {BACKUP}")

nb = json.loads(NB.read_text(encoding="utf-8"))

src12 = nb["cells"][12]["source"]
joined = "".join(src12)

# 멱등성
if "Cell 2 standalone fallback" in joined:
    print("[skip] Cell 12 fallback 이미 적용됨")
    sys.exit(0)

FALLBACK = (
    '# === Cell 2 standalone fallback (Cell 0b 미실행 시 자동 정의) ===\n'
    'import os, sys\n'
    'try:\n'
    '    DRIVE_ROOT\n'
    'except NameError:\n'
    '    if os.path.isdir("/content/drive/MyDrive"):\n'
    '        DRIVE_ROOT = "/content/drive/MyDrive"\n'
    '    elif os.path.isdir(r"H:\\내 드라이브"):\n'
    '        DRIVE_ROOT = r"H:\\내 드라이브"\n'
    '    else:\n'
    '        DRIVE_ROOT = "/content/drive/MyDrive"\n'
    '    print(f"[Cell 2 fallback] DRIVE_ROOT = {DRIVE_ROOT}")\n'
    'try:\n'
    '    _IS_COLAB\n'
    'except NameError:\n'
    '    _IS_COLAB = "google.colab" in sys.modules or os.path.exists("/content")\n'
    'try:\n'
    '    SYNC_ROOT\n'
    'except NameError:\n'
    '    SYNC_ROOT = os.path.join(DRIVE_ROOT, "sync")\n'
    'try:\n'
    '    OUTPUT_DIR\n'
    'except NameError:\n'
    '    OUTPUT_DIR = os.path.join(SYNC_ROOT, "_ocr_extracted")\n'
    '    os.makedirs(OUTPUT_DIR, exist_ok=True)\n'
    'try:\n'
    '    STATE_DIR\n'
    'except NameError:\n'
    '    STATE_DIR = os.path.join(DRIVE_ROOT, ".auto-memory", "ocr_state")\n'
    '    os.makedirs(STATE_DIR, exist_ok=True)\n'
    'try:\n'
    '    PROGRESS_PATH\n'
    'except NameError:\n'
    '    PROGRESS_PATH = os.path.join(STATE_DIR, "progress.json")\n'
    'try:\n'
    '    OFFSET_TABLE_PATH\n'
    'except NameError:\n'
    '    OFFSET_TABLE_PATH = os.path.join(STATE_DIR, "offset_table.json")\n'
    'try:\n'
    '    MATCH_TABLE_PATH\n'
    'except NameError:\n'
    '    MATCH_TABLE_PATH = os.path.join(STATE_DIR, "match_table.json")\n'
    'try:\n'
    '    TORCH_DEVICE\n'
    'except NameError:\n'
    '    try:\n'
    '        import torch\n'
    '        TORCH_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"\n'
    '    except Exception:\n'
    '        TORCH_DEVICE = "cpu"\n'
    '# === fallback 끝 ===\n'
    '\n'
)

new_joined = FALLBACK + joined

# 문법 검증
try:
    ast.parse(new_joined)
    print("  ast.parse OK")
except SyntaxError as e:
    print(f"  [ERROR] SyntaxError: {e}")
    sys.exit(1)

nb["cells"][12]["source"] = new_joined.splitlines(keepends=True)

# 저장
TMP = NB.with_suffix(".ipynb.tmp")
with TMP.open("w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
os.replace(TMP, NB)
print(f"[saved] {NB}")

# 검증
nb2 = json.loads(NB.read_text(encoding="utf-8"))
print(f"[verify] cells={len(nb2['cells'])}")
try:
    import nbformat
    nbformat.validate(nbformat.reads(NB.read_text(encoding="utf-8"), as_version=4))
    print(f"  nbformat.validate OK")
except Exception as e:
    print(f"  nbformat: {e}")

print()
print("[Cell 12 첫 12줄]")
for ln in "".join(nb2["cells"][12]["source"]).splitlines()[:12]:
    print(f"  | {ln}")
