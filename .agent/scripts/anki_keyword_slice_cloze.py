# -*- coding: utf-8 -*-
"""
anki_keyword_slice_cloze.py — cloze 카드 고유 평문(빈칸 벗긴 Text)을 키워드 추출 슬라이스로 분할.
에이전트 출력은 .agent/state/kw_out_cloze/, 병합 결과는 anki_cloze_kw_cache.jsonl (build가 빈칸 보강에 사용).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from anki_deck_build_v4 import collect, cz_plain, cz_key  # noqa: E402

SLICE = 300
OUT_DIR = Path("H:/내 드라이브/.agent/state/kw_slices_cloze")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _basic, cloze, _meta = collect()
    uniq = {}
    for rows in cloze.values():
        for tx, _sc, _tg in rows:
            k = cz_key(tx)
            if k not in uniq:
                uniq[k] = cz_plain(tx)
    items = list(uniq.items())
    n_slices = 0
    for n, i in enumerate(range(0, len(items), SLICE)):
        p = OUT_DIR / f"slice_c{n:02d}.jsonl"
        with p.open("w", encoding="utf-8", newline="\n") as fh:
            for k, a in items[i:i + SLICE]:
                fh.write(json.dumps({"k": k, "a": a}, ensure_ascii=False) + "\n")
        n_slices = n + 1
    print(f"고유 cloze 평문 {len(uniq)}건 → 슬라이스 {n_slices}개 (각 {SLICE}건)")


if __name__ == "__main__":
    main()
