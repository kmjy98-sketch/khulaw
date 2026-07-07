"""ocr_extract_v2.py 의 Cell 1 + Cell 4 통합 테스트.

설치 셀(Cell 0a) 의 sys.exit / restart_session 을 우회하기 위해 INSTALL_FLAG 를
미리 만들어 둔 뒤, 노트북 소스를 한 줄씩 실행한다 (jupytext-like).
"""
from __future__ import annotations
import os, tempfile, sys, runpy, ast, shutil, json

INSTALL_FLAG = os.path.join(tempfile.gettempdir(), "ocr_extract_v2_installed")
open(INSTALL_FLAG, "w").close()

DRIVE_ROOT = r"H:\내 드라이브"
TEST_STATE = os.path.join(DRIVE_ROOT, ".auto-memory", "ocr_state_TEST")
if os.path.isdir(TEST_STATE):
    # 사전 정리: 깨끗한 상태에서 시작
    for f in os.listdir(TEST_STATE):
        os.remove(os.path.join(TEST_STATE, f))
else:
    os.makedirs(TEST_STATE, exist_ok=True)

py_path = os.path.join(DRIVE_ROOT, ".agent", "notebooks", "ocr_extract_v2.py")
with open(py_path, "r", encoding="utf-8") as f:
    src = f.read()

# 셀 분리: '# %%' 단위 (kind 함께 추적)
cells = []  # list of (kind, source)
cur = []
cur_kind = "code"
for ln in src.splitlines():
    if ln.startswith("# %%"):
        if cur:
            cells.append((cur_kind, "\n".join(cur)))
        cur = []
        cur_kind = "markdown" if "[markdown]" in ln else "code"
        continue
    cur.append(ln)
if cur:
    cells.append((cur_kind, "\n".join(cur)))
print(f"cells parsed total: {len(cells)}")

code_cells = [s for (k, s) in cells if k == "code"]
print(f"code cells: {len(code_cells)}")

ns: dict = {"__name__": "__notebook__", "__file__": py_path}

# Code cell 0: Cell 0a (설치, INSTALL_FLAG 로 스킵)
exec(code_cells[0], ns)
# Code cell 1: Cell 0b (import + Drive 마운트 + 경로)
exec(code_cells[1], ns)
# 테스트용 STATE_DIR 로 강제 변경
ns["STATE_DIR"] = TEST_STATE
ns["OFFSET_TABLE_PATH"] = os.path.join(TEST_STATE, "offset_table.json")
ns["PROGRESS_PATH"] = os.path.join(TEST_STATE, "progress.json")

# Code cell 2: Cell 1 (scan_books 자동 호출)
exec(code_cells[2], ns)

print("\n--- offset_table after scan ---")
with open(ns["OFFSET_TABLE_PATH"], "r", encoding="utf-8") as f:
    print(f.read())

# Code cell 3: Cell 2 (extraction). run_extraction() 은 주석 처리돼 있어 정의만 등록.
exec(code_cells[3], ns)
# Code cell 4: Cell 3 (요약)
exec(code_cells[4], ns)

# Code cell 5: Cell 4 (update_offset 정의)
exec(code_cells[5], ns)

# update_offset 호출
update_offset = ns["update_offset"]
table_path = ns["OFFSET_TABLE_PATH"]
with open(table_path) as f:
    table = json.load(f)
book = next(iter(table.keys()))
print(f"\nbefore manual update: offset={table[book]['toc_offset']} method={table[book]['method']}")
update_offset(book, toc_offset=8)
with open(table_path) as f:
    table = json.load(f)
print(f"after  manual update: offset={table[book]['toc_offset']} method={table[book]['method']}")

print("\nINTEGRATION OK")
