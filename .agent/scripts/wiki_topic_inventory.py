# -*- coding: utf-8 -*-
"""
wiki_topic_inventory.py — v4 TSV에서 주제::별 카드 인벤토리 집계
- 쟁점(주제::) × 속성(조문/요건/정의/판례/학설/사례형) 분포 → wiki 아티클 후보 우선순위
- 출력: .agent/state/wiki_topic_inventory.json + 콘솔 상위 30
"""
import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

V4 = Path(vp("outputs", "anki", "v4"))
OUT = Path(vp(".agent", "state", "wiki_topic_inventory.json"))

ATTRS = ["조문", "요건", "정의", "판례", "학설", "사례형", "사례"]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    topics = defaultdict(lambda: {"total": 0, "속성": defaultdict(int), "과목": defaultdict(int), "덱": defaultdict(int)})
    for f in sorted(V4.glob("*.tsv")):
        deck = f.stem.rsplit("_", 1)[0]
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or "\t" not in line:
                continue
            tags = line.rsplit("\t", 1)[-1]
            subj = re.search(r"과목::(\S+)", tags)
            attrs = re.findall(r"속성::(\S+)", tags)
            for t in re.findall(r"주제::(\S+)", tags):
                d = topics[t]
                d["total"] += 1
                d["덱"][deck] += 1
                if subj:
                    d["과목"][subj.group(1)] += 1
                for a in attrs:
                    d["속성"][a] += 1

    ranked = sorted(topics.items(), key=lambda kv: -kv[1]["total"])
    OUT.write_text(
        json.dumps(
            {t: {k: (dict(v) if isinstance(v, defaultdict) else v) for k, v in d.items()} for t, d in ranked},
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )
    print(f"주제 수: {len(ranked)} / 카드-주제 연결: {sum(d['total'] for _, d in ranked)}")
    print("\n상위 30 (주제 | 총 | 조문/요건/정의/판례/학설/사례):")
    for t, d in ranked[:30]:
        a = d["속성"]
        subj = max(d["과목"], key=d["과목"].get) if d["과목"] else "?"
        print(f"  {t} [{subj}] {d['total']} | {a.get('조문',0)}/{a.get('요건',0)}/{a.get('정의',0)}/{a.get('판례',0)}/{a.get('학설',0)}/{a.get('사례형',0)+a.get('사례',0)}")


if __name__ == "__main__":
    sys.exit(main())
