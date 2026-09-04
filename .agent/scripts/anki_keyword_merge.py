# -*- coding: utf-8 -*-
"""
anki_keyword_merge.py — 에이전트 키워드 산출물(kw_out/, kw_out_cloze/)을 검증·병합.
- 검증: 키워드가 해당 카드 원문(a)에 '그대로' 존재해야 채택 (부분 문자열 검사)
- 출력: .agent/state/anki_keyword_cache.jsonl(basic) / anki_cloze_kw_cache.jsonl(cloze)
- 멱등: 슬라이스·산출물 전체를 다시 읽어 캐시를 새로 쓴다 (재실행 안전)
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

STATE = Path(vp(".agent", "state"))
JOBS = [
    ("kw_slices", "kw_out", "anki_keyword_cache.jsonl"),
    ("kw_slices_cloze", "kw_out_cloze", "anki_cloze_kw_cache.jsonl"),
]

# ── v2 한국어 경계 검증기 (08_빈칸키워드_기준_v2.md §4) ──────────────────
P_NEXT = set("에을를이가은는의로와과도며만")   # 빈칸 끝 바로 뒤에 와도 자연스러운 조사 시작 글자
PART_CH = set("을를이가은는의에로와과도")      # 단독 조사 어절 판별용
CASE_TRIM = set("을를은는")  # 어절 끝 격조사 트리밍 대상. 의(죄형법정주의·동의)·가(재평가)·이(길이)·로(므로)·에 는 어말 혼동으로 제외
TRAIL_FUNC = {"관한", "대한", "의한", "따른", "인한", "위한", "관하여", "대하여", "대해", "관해", "있어서"}
LEAD_FUNC = {"그", "이", "그러한", "이러한", "한편", "또한", "즉", "다만", "및", "또는"}
STOP = {"경우", "때", "것", "수", "등", "있다", "한다", "된다", "본다"}


def _hangul(ch: str) -> bool:
    return "가" <= ch <= "힣"


def normalize_kw(kw: str, a: str):
    """키워드를 한국어 어절·조사 경계에 맞게 보정. 보정 불가능한 파편은 None."""
    if len(kw) < 2:
        return None
    i = a.find(kw)
    if i < 0:
        return None
    j = i + len(kw)
    if i > 0 and _hangul(a[i - 1]):           # 시작이 단어 중간 → 다음 어절로
        sp = kw.find(" ")
        if sp < 0:
            return None
        i += sp + 1
    if j < len(a) and _hangul(a[j]) and a[j] not in P_NEXT:  # 끝이 내용어 중간 → 직전 어절로
        sp = a[i:j].rfind(" ")
        if sp < 0:
            return None
        j = i + sp
    words = a[i:j].strip().split()
    while words and (
        words[-1] in TRAIL_FUNC
        or (len(words[-1]) <= 2 and all(c in PART_CH for c in words[-1]))
    ):
        words.pop()
    while words and words[0] in LEAD_FUNC:
        words.pop(0)
    if not words:
        return None
    w = words[-1]
    if len(w) >= 3 and w[-1] in CASE_TRIM:    # "범위를"→"범위", "법률의"→"법률"
        words[-1] = w[:-1]
    s = " ".join(words)
    if len(s) < 2 or s in STOP or s not in a:
        return None
    return s


def load_jsonl(p: Path):
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip().lstrip("﻿")
        if not line or line.startswith("```"):
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for slice_dir, out_dir, cache_name in JOBS:
        sdir, odir = STATE / slice_dir, STATE / out_dir
        if not sdir.exists():
            continue
        ref = {}  # k -> 원문 a
        for p in sorted(sdir.glob("*.jsonl")):
            for o in load_jsonl(p):
                ref[o["k"]] = o["a"]
        cache, bad_kw, unknown_k = {}, 0, 0
        if odir.exists():
            for p in sorted(odir.glob("*.jsonl")):
                for o in load_jsonl(p):
                    k, kws = o.get("k"), o.get("kw") or []
                    if k not in ref:
                        unknown_k += 1
                        continue
                    a = ref[k]
                    ok = []
                    for kw in kws:
                        nk = normalize_kw(str(kw).strip(), a)
                        if nk and nk not in ok:
                            ok.append(nk)
                        elif kw:
                            bad_kw += 1
                    if ok:
                        cache[k] = ok
        out = STATE / cache_name
        with out.open("w", encoding="utf-8", newline="\n") as fh:
            for k, kws in cache.items():
                fh.write(json.dumps({"k": k, "kw": kws}, ensure_ascii=False) + "\n")
        n_kw = sum(len(v) for v in cache.values())
        print(f"[{cache_name}] 대상 {len(ref)} / 캐시 {len(cache)} ({len(ref) and cache and round(len(cache)*100/len(ref))}%) / 키워드 {n_kw} / 원문불일치 폐기 {bad_kw} / 미상키 {unknown_k}")


if __name__ == "__main__":
    main()
