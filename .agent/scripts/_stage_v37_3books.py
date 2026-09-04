# -*- coding: utf-8 -*-
"""3책 카드(02_cards/*_cards.md) → 02_cards_v37/*_v37.md 스테이징(복사). #16-C 로그 3종 append. 비파괴."""
import os, re, csv, json, shutil, hashlib, sys
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = "H:/내 드라이브/outputs/02_cards"
DST = "H:/내 드라이브/outputs/02_cards_v37"
LOG = "H:/내 드라이브/.agent/file_ops_log"
PREFIXES = ("쟁점노트_소송집행_", "쟁점노트_가족법_", "기초법리집행법_")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


files = [f for f in os.listdir(SRC) if f.endswith("_cards.md") and f.startswith(PREFIXES)]
staged = []
for f in sorted(files):
    txt = open(os.path.join(SRC, f), encoding="utf-8").read()
    if len(re.findall(r"(?m)^### ", txt)) < 5:
        print("skip(보고서):", f)
        continue
    staged.append(f)

rows = []
ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
for f in staged:
    s = os.path.join(SRC, f)
    dname = f.replace("_cards.md", "_v37.md")
    d = os.path.join(DST, dname)
    shutil.copy2(s, d)
    sh = sha(s)
    ok = sha(d) == sh
    sz = os.path.getsize(s)
    rows.append((ts, "copy", s.replace("/", "\\"), d.replace("/", "\\"), sz, sh, "",
                 "3책 v37 스테이징(apkg 빌드용)", ok))
    print(("OK   " if ok else "FAIL ") + dname)

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

print(f"\n스테이징 {len(rows)}건 (검증 {sum(1 for r in rows if r[8])}건 OK), 로그 3종 append 완료")
