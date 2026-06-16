"""ocr_extract_v2.ipynb 전수 audit — 코드 변경 X, 분석만."""
import json, re
from pathlib import Path

NB = Path(r"H:\내 드라이브\ocr_extract_v2.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))

code_cells = [(i, "".join(c["source"])) for i, c in enumerate(nb["cells"]) if c["cell_type"] == "code"]
print(f"총 코드 셀: {len(code_cells)}개\n")

# 패턴별 검사
patterns = [
    ("DEPRECATED_API_RESTART", r"runtime\.restart_session"),
    ("DEPRECATED_API_OTHER",   r"colab\.runtime\."),
    ("DRIVE_WRITE_HARDCODE",   r"open\(.*DRIVE_ROOT|open\(.*SYNC_ROOT|open\(.*OUTPUT_DIR|open\(.*STATE_DIR"),
    ("_SAVE_JSON_ATOMIC",      r"_save_json_atomic"),
    ("BARE_EXCEPT",            r"except\s*:\s*(?:#|$)"),
    ("EXCEPT_EXCEPTION_PASS",  r"except\s+Exception:?\s*\n\s+pass\b"),
    ("SUBPROCESS_NO_TIMEOUT",  r"subprocess\.run\([^)]*\)"),
    ("SUBPROCESS_CHECK_CALL",  r"subprocess\.check_call"),
    ("DRIVE_MOUNT",            r"drive\.mount"),
    ("OS_KILL",                r"os\.kill"),
    ("ENV_GET_NO_DEFAULT",     r"os\.environ\[\"OCR_"),
    ("ENV_GETENV_FLOAT_INT",   r"int\(os\.environ|float\(os\.environ"),
    ("RSYNC",                  r"\brsync\b"),
    ("CP_RU",                  r"\bcp -ru\b|'cp', '-ru'|\"cp\", \"-ru\""),
    ("PROGRESS_SAVE",          r"save_progress\("),
    ("PDFCONVERTER",           r"PdfConverter|create_model_dict"),
    ("FREE_MEMORY",            r"_free_memory|gc\.collect|torch\.cuda\.empty_cache"),
    ("MAX_RAM_CHECK",          r"OCR_MAX_RAM_GB|_get_ram_gb|MEMORY_INFO"),
    ("HF_VARS",                r"HF_HUB_CACHE|HF_HOME|TRANSFORMERS_CACHE"),
    ("WINDOWS_PATH",           r"H:\\\\|H:/|/mnt/h/"),
    ("SEED_FUNC_CALL",         r"seed_to_drive\(\)|seed_in_from_drive\(\)"),
    ("CELL_INDEX_LABEL",       r"\[Cell\s+\d[a-z]?\]"),
    ("PRINT_KOREAN",           r"print\([^)]*[가-힣]"),
]

findings = {}
for label, pat in patterns:
    findings[label] = []
    rgx = re.compile(pat)
    for i, src in code_cells:
        for m in rgx.finditer(src):
            ln_start = src.rfind("\n", 0, m.start()) + 1
            ln_end = src.find("\n", m.end())
            if ln_end < 0: ln_end = len(src)
            line = src[ln_start:ln_end].strip()
            findings[label].append((i, line))

# 출력
for label, hits in findings.items():
    if not hits:
        continue
    print(f"### {label} — {len(hits)}건")
    for i, line in hits[:8]:
        if len(line) > 110:
            line = line[:110] + "..."
        print(f"  cell {i:>2}: {line}")
    if len(hits) > 8:
        print(f"  ... +{len(hits)-8}건")
    print()
