"""Cell 4의 잘못된 google.colab.runtime.restart_runtime() 호출을 다중 fallback으로 교체."""
import json, os, shutil, ast, sys, io
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

NB = Path(r"H:\내 드라이브\ocr_extract_v2.ipynb")
ts = datetime.now().strftime("%Y-%m-%d_%H%M")
BACKUP = Path(r"H:\내 드라이브\5.기타") / f"ocr_extract_v2.bak_{ts}_restart_fix.ipynb"

print("=" * 70); print("STEP 1 — 백업"); print("=" * 70)
BACKUP.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(NB, BACKUP)
print(f"  bak = {BACKUP}")
print(f"  size = {BACKUP.stat().st_size:,} bytes")

print()
print("=" * 70); print("STEP 2 — 패치 (Cell 4 restart fallback)"); print("=" * 70)
nb = json.loads(NB.read_text(encoding="utf-8"))
src = nb["cells"][4]["source"]
joined = "".join(src)

# 멱등성 검사
if "_colab_kernel" in joined or "do_shutdown" in joined:
    print("  [skip] 이미 fallback 적용됨")
    sys.exit(0)

OLD = (
    '        print("[Cell 0a] Colab: 런타임을 재시작합니다. 재시작 후 다시 [런타임 > 모두 실행].")\n'
    '        import google.colab  # noqa: F401\n'
    '        google.colab.runtime.restart_runtime() # Corrected line\n'
)
NEW = (
    '        print("[Cell 0a] Colab: 런타임을 재시작합니다. 재시작 후 다시 [런타임 > 모두 실행].")\n'
    '        try:\n'
    '            from google.colab import kernel as _colab_kernel\n'
    '            _colab_kernel.restart_execution()\n'
    '        except Exception as _e1:\n'
    '            print(f"[Cell 0a] kernel.restart_execution 실패: {_e1} → IPython fallback")\n'
    '            try:\n'
    '                from IPython.core.application import Application\n'
    '                Application.instance().kernel.do_shutdown(True)\n'
    '            except Exception as _e2:\n'
    '                print(f"[Cell 0a] IPython fallback 실패: {_e2} → 강제 종료")\n'
    '                os.kill(os.getpid(), 9)\n'
)

if OLD not in joined:
    print(f"  [ERROR] 매칭 실패. 현재 Cell 4 restart 라인:")
    for ln in src:
        if "restart" in ln.lower() or "google.colab" in ln.lower():
            print(f"    | {ln.rstrip()}")
    sys.exit(1)

new_joined = joined.replace(OLD, NEW, 1)
nb["cells"][4]["source"] = new_joined.splitlines(keepends=True)

# 문법 검증
try:
    ast.parse(new_joined)
    print("  ast.parse OK")
except SyntaxError as e:
    print(f"  [ERROR] SyntaxError: {e}")
    sys.exit(2)

# 저장
TMP = NB.with_suffix(".ipynb.tmp")
with TMP.open("w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
os.replace(TMP, NB)
print(f"  saved = {NB}")

print()
print("=" * 70); print("STEP 3 — 검증"); print("=" * 70)
nb2 = json.loads(NB.read_text(encoding="utf-8"))
print(f"  cells = {len(nb2['cells'])} / nbformat = {nb2['nbformat']}.{nb2.get('nbformat_minor')}")

try:
    import nbformat
    nbformat.validate(nbformat.reads(NB.read_text(encoding="utf-8"), as_version=4))
    print(f"  nbformat.validate OK")
except Exception as e:
    print(f"  nbformat.validate: {e}")

src4 = "".join(nb2["cells"][4]["source"])
import re
checks = [
    ("restart_runtime 제거", lambda s: "restart_runtime" not in s),
    ("restart_session 제거", lambda s: "restart_session" not in s),
    ("kernel.restart_execution 존재", lambda s: "_colab_kernel.restart_execution()" in s),
    ("IPython fallback 존재", lambda s: "do_shutdown(True)" in s),
    ("os.kill fallback 존재", lambda s: "os.kill(os.getpid(), 9)" in s),
]
for label, fn in checks:
    print(f"  {'✓' if fn(src4) else '✗'} {label}")

print()
print("패치된 Cell 4 restart 영역:")
for ln in src4.splitlines():
    if "kernel" in ln.lower() or "restart" in ln.lower() or "do_shutdown" in ln or "os.kill" in ln:
        print(f"  | {ln.rstrip()}")
