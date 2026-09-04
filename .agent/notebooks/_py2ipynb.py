"""percent-format .py → .ipynb 단순 변환기.

지원 토큰:
    # %%               → 새 코드 셀
    # %% [markdown]    → 새 마크다운 셀 (이후의 `# ` 시작 줄에서 한 칸 prefix 제거)
"""
from __future__ import annotations

import sys
import nbformat as nbf


def convert(py_path: str, ipynb_path: str) -> None:
    with open(py_path, "r", encoding="utf-8") as f:
        text = f.read()

    nb = nbf.v4.new_notebook()
    cells: list = []
    cur_kind = "code"
    cur_lines: list[str] = []

    def flush() -> None:
        if not cur_lines and not cells:
            return
        if not cur_lines:
            return
        body = "\n".join(cur_lines).rstrip("\n")
        if cur_kind == "markdown":
            stripped = []
            for ln in body.splitlines():
                if ln.startswith("# "):
                    stripped.append(ln[2:])
                elif ln == "#":
                    stripped.append("")
                else:
                    stripped.append(ln)
            cells.append(nbf.v4.new_markdown_cell("\n".join(stripped)))
        else:
            if body.strip() == "":
                return
            cells.append(nbf.v4.new_code_cell(body))

    lines = text.splitlines()
    i = 0
    # 첫 셀 헤더 전까지 무시되는 prelude 는 없다고 가정 (우리 파일은 # %% 로 시작).
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith("# %%"):
            flush()
            cur_lines = []
            cur_kind = "markdown" if "[markdown]" in s else "code"
            i += 1
            continue
        cur_lines.append(ln)
        i += 1
    flush()

    nb.cells = cells
    # validate
    nbf.validate(nb)
    with open(ipynb_path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"OK  cells={len(cells)}  → {ipynb_path}")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
