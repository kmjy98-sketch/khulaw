# -*- coding: utf-8 -*-
"""Dryrun for Cell 0a: validate that the install logic produces the right
pip-install command for Colab AND for local CPU, without actually running pip.

We intercept subprocess.check_call by replacing the real subprocess module in
sys.modules BEFORE the cell source imports it.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import types
from pathlib import Path

NB_PY = Path(r"H:\내 드라이브\.agent\notebooks\paddle_ocr_pipeline.py")
src = NB_PY.read_text(encoding="utf-8")

# Stop the file at end of Cell 0a
m = re.search(r"^# %% \[markdown\]\n# # Cell 0b:", src, flags=re.M)
assert m, "couldn't find Cell 0b header"
cell0a_src = src[: m.start()]


def make_subproc_stub(recorder: list):
    """Return a fake `subprocess` module recording every check_call invocation."""
    fake = types.ModuleType("subprocess")
    def fake_check_call(cmd, **kw):
        recorder.append(list(cmd))
    fake.check_call = fake_check_call
    fake.run = lambda *a, **k: types.SimpleNamespace(returncode=0, stdout="", stderr="")
    fake.PIPE = -1
    fake.STDOUT = -2
    fake.DEVNULL = -3
    return fake


def make_colab_stub():
    g = types.ModuleType("google")
    gc = types.ModuleType("google.colab")
    class _Rt:
        @staticmethod
        def restart_session(): print("    [stub] runtime.restart_session()")
    gc.runtime = _Rt()
    g.colab = gc
    return g, gc


def run_case(label: str, *, is_colab: bool):
    print(f"\n=== {label} ===")
    recorder: list = []
    sys.modules["subprocess"] = make_subproc_stub(recorder)

    if is_colab:
        g, gc = make_colab_stub()
        sys.modules["google"] = g
        sys.modules["google.colab"] = gc
    else:
        sys.modules.pop("google", None)
        sys.modules.pop("google.colab", None)

    TMP = Path(tempfile.mkdtemp(prefix="cell0a_"))
    flag = TMP / f"flag_{label.replace(' ', '_')}"
    if is_colab:
        content_dir = TMP / "content"
        content_dir.mkdir()
        patched = cell0a_src.replace(
            "os.path.exists('/content')",
            f"os.path.exists(r'{content_dir}')",
        )
    else:
        patched = cell0a_src.replace("os.path.exists('/content')", "False")
    patched = patched.replace(
        "INSTALL_FLAG = os.path.join(tempfile.gettempdir(), 'paddle_installed')",
        f"INSTALL_FLAG = r'{flag}'",
    )

    glb = {"__name__": "__main__", "__file__": str(NB_PY)}
    exec(patched, glb)

    print("Calls recorded:")
    for c in recorder:
        # Drop the python.exe path for readability
        rest = [a for a in c if "python" not in a.lower() or a.startswith("-")]
        print("  pip", " ".join(rest))

    return recorder


# --- Colab simulation ---
calls_a = run_case("TEST A: simulate Colab", is_colab=True)

cmd_a = [" ".join(c) for c in calls_a]
print("\nAssertions for Colab:")
checks = {
    "paddlepaddle-gpu==3.2.1": any("paddlepaddle-gpu==3.2.1" in s for s in cmd_a),
    "cu126 index URL":         any("paddlepaddle.org.cn/packages/stable/cu126" in s for s in cmd_a),
    "paddleocr==3.5.0":        any("paddleocr==3.5.0" in s for s in cmd_a),
    "paddlex[ocr]==3.5.1":     any("paddlex[ocr]==3.5.1" in s for s in cmd_a),
    "two-step install":        len(calls_a) == 2,
    "first call has -i flag":  ("-i" in calls_a[0] and "paddlepaddle-gpu==3.2.1" in calls_a[0]) if calls_a else False,
    "second call lacks -i":    ("-i" not in calls_a[1]) if len(calls_a) > 1 else False,
}
for k, v in checks.items():
    print(f"  [{'OK' if v else 'FAIL'}] {k}")
assert all(checks.values()), "Colab checks failed"

# --- Local CPU simulation ---
calls_b = run_case("TEST B: simulate local CPU", is_colab=False)
cmd_b = [" ".join(c) for c in calls_b]
print("\nAssertions for local CPU:")
checks_b = {
    "paddlepaddle==3.0.0 (CPU)": any("paddlepaddle==3.0.0" in s for s in cmd_b),
    "no GPU package":            all("paddlepaddle-gpu" not in s for s in cmd_b),
    "paddleocr==3.5.0":          any("paddleocr==3.5.0" in s for s in cmd_b),
    "paddlex[ocr]==3.5.1":       any("paddlex[ocr]==3.5.1" in s for s in cmd_b),
    "single call":               len(calls_b) == 1,
    "no -i flag":                all("-i" not in c for c in calls_b),
}
for k, v in checks_b.items():
    print(f"  [{'OK' if v else 'FAIL'}] {k}")
assert all(checks_b.values()), "Local CPU checks failed"

print("\nALL CELL 0A DRYRUN ASSERTIONS PASS")
