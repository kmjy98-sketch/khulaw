# -*- coding: utf-8 -*-
"""코워크 이관 번들 생성: apkg(과목/책종류) + 리포트 + 신규3책 카드md 를 5.기타/문서/ 하위로 집결. #16-C 로그. 비파괴(복사)."""
import os, csv, json, shutil, hashlib, sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = VAULT_ROOT
EXPORT = f"{WS}/5.기타/문서/_cowork_export_카드v37_2026-06-21"
APKG_SRC = f"{WS}/outputs/anki/v37/apkg"
CARDS_SRC = f"{WS}/outputs/02_cards"
STATE = f"{WS}/.agent/state"
LOG = f"{WS}/.agent/file_ops_log"
PREFIXES = ("쟁점노트_소송집행_", "쟁점노트_가족법_", "기초법리집행법_")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


rows = []
ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def copy_log(s, d, reason):
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copy2(s, d)
    shh = sha(s)
    ok = sha(d) == shh
    rows.append((ts, "copy", s.replace("/", "\\"), d.replace("/", "\\"),
                 os.path.getsize(s), shh, "", reason, ok))


# 1) apkg 트리(과목/책종류) 복제
n_apkg = 0
for root, _, fs in os.walk(APKG_SRC):
    for f in sorted(fs):
        if f.endswith(".apkg"):
            rel = os.path.relpath(os.path.join(root, f), APKG_SRC)
            copy_log(os.path.join(root, f), os.path.join(EXPORT, "apkg", rel), "코워크번들:apkg")
            n_apkg += 1

# 2) 리포트
copy_log(f"{APKG_SRC}/_apkg_report.md", f"{EXPORT}/reports/apkg_build_report.md", "코워크번들:빌드리포트")
copy_log(f"{STATE}/caseno_verify_3books_report.md", f"{EXPORT}/reports/caseno_verify_3books_report.md", "코워크번들:DRF검증리포트")

# 3) 신규 3책 카드 md(본문+색인)
n_md = 0
for f in sorted(os.listdir(CARDS_SRC)):
    if f.endswith("_cards.md") and f.startswith(PREFIXES):
        copy_log(os.path.join(CARDS_SRC, f), f"{EXPORT}/cards_md_신규3책/{f}", "코워크번들:3책카드md")
        n_md += 1

# 로그 append (#16-C)
with open(os.path.join(LOG, "master.csv"), "a", encoding="utf-8", newline="") as fp:
    w = csv.writer(fp)
    for r in rows:
        w.writerow(list(r))
with open(os.path.join(LOG, "master.jsonl"), "a", encoding="utf-8") as fp:
    for r in rows:
        fp.write(json.dumps({"timestamp": r[0], "operation": r[1], "source_path": r[2],
                             "dest_path": r[3], "size_bytes": r[4], "sha256": r[5],
                             "task_id": r[6], "reason": r[7], "verified": bool(r[8])},
                            ensure_ascii=False) + "\n")
with open(os.path.join(LOG, "master.md"), "a", encoding="utf-8") as fp:
    for r in rows:
        fp.write(f"| {r[0]} | {r[1]} | `{r[2]}` | `{r[3]}` | {r[4]} | `{r[5][:12]}…` | — | {r[7]} | {'OK' if r[8] else 'FAIL'} |\n")

allok = all(r[8] for r in rows)
print(f"apkg {n_apkg} + 리포트 2 + 카드md {n_md} = 복사 {len(rows)}건, 검증 {'전부 OK' if allok else 'FAIL 포함!'}")
print("번들:", EXPORT.replace("/", "\\"))
