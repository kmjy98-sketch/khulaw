# -*- coding: utf-8 -*-
"""민소사례 카드(02_cards/*_cards.md) → 02_cards_v37/*_v37.md 스테이징(정본 반영). #16-C 로그. 비파괴. ≥5### 필터(빈청크 제외)."""
import os, re, csv, json, shutil, hashlib, sys
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = "H:/내 드라이브/outputs/02_cards"
DST = "H:/내 드라이브/outputs/02_cards_v37"
LOG = "H:/내 드라이브/.agent/file_ops_log"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


files = [f for f in os.listdir(SRC) if f.endswith("_cards.md") and f.startswith("민소사례")]
staged, rows = [], []
ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
for f in sorted(files):
    txt = open(os.path.join(SRC, f), encoding="utf-8").read()
    if len(re.findall(r"(?m)^### ", txt)) < 5:
        print("skip(빈/소청크):", f)
        continue
    s = os.path.join(SRC, f)
    d = os.path.join(DST, f.replace("_cards.md", "_v37.md"))
    shutil.copy2(s, d)
    sh = sha(s)
    ok = sha(d) == sh
    rows.append((ts, "copy", s.replace("/", "\\"), d.replace("/", "\\"),
                 os.path.getsize(s), sh, "", "민소사례 정본(v37) 스테이징", ok))
    print(("OK   " if ok else "FAIL ") + os.path.basename(d))

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
print(f"\n민소사례 스테이징 {len(rows)}건 (검증 {sum(1 for r in rows if r[8])} OK), 로그 3종 append")
