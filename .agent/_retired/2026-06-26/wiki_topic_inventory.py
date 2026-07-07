# -*- coding: utf-8 -*-
"""
wiki_topic_inventory.py — 소스 카드(02_cards_v37)의 인라인 주제::별 카드 인벤토리 집계.
- 2026-06-25: 입력을 구버전 v4 TSV(부재·주제::태그 없음) → 소스 카드 md로 전환.
  인라인 과목::/속성::/주제:: 태그를 직접 파싱(원래 태그 로직 유지, 읽는 소스만 교체).
- 쟁점(주제::) × 속성 × 과목 분포 → wiki 아티클 후보 우선순위.
- 출력: .agent/state/wiki_topic_inventory.json + 콘솔 상위 30.
- 파일럿: --limit N(앞 N파일) / --dry(json 미기록).
"""
import json
import os
import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import vp  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = Path(vp("outputs", "02_cards_v37"))
OUT = Path(vp(".agent", "state", "wiki_topic_inventory.json"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="파일럿: 앞 N개 파일만")
    ap.add_argument("--dry", action="store_true", help="json 미기록(파일럿 검토용)")
    a = ap.parse_args()

    topics = defaultdict(lambda: {"total": 0, "속성": defaultdict(int), "과목": defaultdict(int), "덱": defaultdict(int)})
    files = sorted(SRC.glob("*.md"))
    if a.limit:
        files = files[:a.limit]
    n_files = 0
    for f in files:
        book = re.split(r"_(?:llamaparse_)?p[\d-]", f.name)[0]  # 책 prefix → 덱
        used = False
        for line in f.read_text(encoding="utf-8").splitlines():
            if "주제::" not in line:
                continue
            subj = re.search(r"과목::([^\s<>]+)", line)
            attrs = re.findall(r"속성::([^\s<>]+)", line)
            for t in re.findall(r"주제::([^\s<>]+)", line):
                d = topics[t]
                d["total"] += 1
                d["덱"][book] += 1
                if subj:
                    d["과목"][subj.group(1)] += 1
                for at in attrs:
                    d["속성"][at] += 1
                used = True
        if used:
            n_files += 1

    ranked = sorted(topics.items(), key=lambda kv: -kv[1]["total"])
    if not a.dry:
        OUT.write_text(
            json.dumps(
                {t: {k: (dict(v) if isinstance(v, defaultdict) else v) for k, v in d.items()} for t, d in ranked},
                ensure_ascii=False, indent=1,
            ),
            encoding="utf-8",
        )
    tag = " (dry)" if a.dry else ""
    print(f"태그 파일 {n_files} / 주제 수: {len(ranked)} / 주제 출현: {sum(d['total'] for _, d in ranked)}{tag}")
    print("\n상위 30 (주제 [과목] 총 | 속성):")
    for t, d in ranked[:30]:
        subj = max(d["과목"], key=d["과목"].get) if d["과목"] else "?"
        attrs = ",".join(f"{k}{v}" for k, v in sorted(d["속성"].items(), key=lambda x: -x[1])[:4])
        print(f"  {t} [{subj}] {d['total']} | {attrs}")


if __name__ == "__main__":
    sys.exit(main())
