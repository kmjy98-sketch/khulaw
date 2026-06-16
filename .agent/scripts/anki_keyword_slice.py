# -*- coding: utf-8 -*-
"""
anki_keyword_slice.py — Basic 카드 고유 Back을 키워드 추출용 슬라이스(jsonl)로 분할.
에이전트가 슬라이스별로 핵심 키워드를 추출해 .agent/state/kw_out/에 기록하면
anki_keyword_merge.py가 검증·병합해 anki_keyword_cache.jsonl을 만든다.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from anki_deck_build_v4 import collect, bk_key  # noqa: E402

SLICE = 300
OUT_DIR = Path("H:/내 드라이브/.agent/state/kw_slices")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    basic, _cloze, _meta = collect()
    uniq = {}
    for rows in basic.values():
        for fr, bk, _sc, _tg in rows:
            k = bk_key(bk)
            if k not in uniq:
                uniq[k] = (fr, bk)
    items = list(uniq.items())
    n_slices = 0
    for n, i in enumerate(range(0, len(items), SLICE)):
        p = OUT_DIR / f"slice_{n:02d}.jsonl"
        with p.open("w", encoding="utf-8", newline="\n") as fh:
            for k, (fr, bk) in items[i:i + SLICE]:
                fh.write(json.dumps({"k": k, "q": fr, "a": bk}, ensure_ascii=False) + "\n")
        n_slices = n + 1
    print(f"고유 Back {len(uniq)}건 → 슬라이스 {n_slices}개 (각 {SLICE}건)")


if __name__ == "__main__":
    main()
