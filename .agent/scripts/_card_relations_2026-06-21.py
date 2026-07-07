#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v37 카드 간 관계(NLP) 분석.
- 같은 사건번호(판례)를 서로 다른 책에서 카드화 → 중복/관계 그룹
- 앞면+키워드 Jaccard 유사도 기반 중복 후보 (anchor 버킷 내 비교로 O(n^2) 회피)
- 주제(frontmatter 태그) / 키워드 클러스터
출력: 9.작업중/클로드/카드관계분석_2026-06-21.md + .agent/state/_card_relations_2026-06-21.json
"""
import os, re, json, glob, itertools
from collections import defaultdict

CARD_DIR = r"H:\내 드라이브\outputs\02_cards_v37"
OUT_MD   = r"H:\내 드라이브\9.작업중/클로드\카드관계분석_2026-06-21.md"
OUT_JSON = r"H:\내 드라이브\.agent\state\_card_relations_2026-06-21.json"

HEAD_RE  = re.compile(r"^(#{2,6})\s+(.*)$")
ATTR_RE  = re.compile(r"\[([^\]]+)\]")
CLOZE_RE = re.compile(r"\{\{\s*(?:c\d+\s*::)?\s*(.*?)\s*\}\}", re.S)
CASE_RE  = re.compile(r"\d{2,4}(?:다|도|두|헌[가-힣]|가합|가단|나|므|드|허|후|마|바|아|카|초|코)\d+(?:\,?\s*\d+)*")
JOMUN_RE = re.compile(r"제\s*\d+조(?:의\s*\d+)?")
JUJE_RE  = re.compile(r"주제::([^\s]+)")
GWAMOK_RE= re.compile(r"과목::([^\s]+)")
FRONT_RE = re.compile(r"^\s*(?:\*\*\s*)?(?:앞면?|앞)\s*(?:\*\*)?\s*[:：]?\s*(.*)$")

STOP = set("그 이 저 것 수 등 및 또 또는 그리고 하는 하지 한다 되는 위한 관한 대한 경우 때 의 를 을 가 은 는 에 와 과 로 도 더 만 본 각 그러나 다만 한편 따라서 즉".split())


def tokenize(s):
    s = CLOZE_RE.sub(lambda m: m.group(1), s)
    s = re.sub(r"\*\*|__|`|>|#", " ", s)
    toks = re.findall(r"[가-힣A-Za-z0-9]{2,}", s)
    return set(t for t in toks if t not in STOP and not t.isdigit())


def split_cards(text):
    lines = text.split("\n")
    cards, cur, head, attr, section = [], [], None, None, None
    def flush():
        if head is not None:
            cards.append({"head": head, "attr": attr, "section": section, "body": "\n".join(cur)})
    for ln in lines:
        m = HEAD_RE.match(ln)
        if m:
            lvl, title = len(m.group(1)), m.group(2).strip()
            am = ATTR_RE.search(title)
            if lvl == 2 and not am:
                flush(); cur, head, attr = [], None, None; section = title; continue
            flush(); cur, head, attr = [], title, (am.group(1) if am else None)
        elif head is not None:
            cur.append(ln)
    flush()
    return cards


def front_of(body):
    for ln in body.split("\n"):
        m = FRONT_RE.match(ln)
        if m and m.group(1).strip():
            return m.group(1).strip()
        if m:
            return ""
    return ""


def main():
    files = sorted(glob.glob(os.path.join(CARD_DIR, "*.md")))
    cards = []
    for fp in files:
        fname = os.path.basename(fp)
        try:
            with open(fp, encoding="utf-8") as f:
                txt = f.read()
        except Exception:
            continue
        gwamok = (GWAMOK_RE.search(txt) or [None, None])[1] if GWAMOK_RE.search(txt) else None
        fm = txt.split("---")
        juje_fm = JUJE_RE.findall(txt)
        for c in split_cards(txt):
            if not c["head"]:
                continue
            full = c["head"] + "\n" + c["body"]
            cases = set(CASE_RE.findall(full))
            joms  = set(re.sub(r"\s+", "", x) for x in JOMUN_RE.findall(full))
            cid = f"{fname} :: {c['head'][:48]}"
            cards.append({
                "id": cid, "file": fname, "attr": c["attr"], "section": c["section"],
                "front": front_of(c["body"])[:80], "cases": cases, "joms": joms,
                "kw": tokenize(full), "gwamok": gwamok,
            })

    # 1) 같은 사건번호 → 그룹 (서로 다른 책 우선)
    by_case = defaultdict(list)
    for i, c in enumerate(cards):
        for cs in c["cases"]:
            by_case[cs].append(i)
    shared_prec = []
    for cs, idxs in by_case.items():
        if len(idxs) < 2:
            continue
        books = sorted(set(cards[i]["file"].split("_p")[0].split("_llamaparse")[0] for i in idxs))
        shared_prec.append({
            "caseno": cs, "n_cards": len(idxs), "n_books": len(books), "books": books,
            "cards": [cards[i]["id"] for i in idxs][:12],
        })
    shared_prec.sort(key=lambda x: (-x["n_books"], -x["n_cards"]))
    cross_book_prec = [g for g in shared_prec if g["n_books"] >= 2]

    # 2) 중복 후보: 같은 사건번호 버킷 내 front+kw Jaccard >= 0.55
    dup_candidates = []
    seen_pairs = set()
    for cs, idxs in by_case.items():
        if len(idxs) < 2 or len(idxs) > 40:
            continue
        for a, b in itertools.combinations(idxs, 2):
            key = (a, b)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            ca, cb = cards[a], cards[b]
            if ca["file"] == cb["file"]:
                continue
            ua, ub = ca["kw"], cb["kw"]
            if not ua or not ub:
                continue
            j = len(ua & ub) / len(ua | ub)
            if j >= 0.55:
                dup_candidates.append({
                    "sim": round(j, 2), "shared_case": cs,
                    "a": ca["id"], "b": cb["id"],
                    "a_front": ca["front"], "b_front": cb["front"],
                })
    dup_candidates.sort(key=lambda x: -x["sim"])

    # 3) 주제/과목 분포 + 다책 등장 주제(키워드)
    kw_books = defaultdict(set)
    for c in cards:
        for k in c["kw"]:
            if len(k) >= 3:
                kw_books[k].add(c["file"].split("_p")[0].split("_llamaparse")[0])
    cross_topic = sorted(((k, len(v)) for k, v in kw_books.items() if len(v) >= 4),
                         key=lambda x: -x[1])[:60]

    report = {
        "total_cards": len(cards), "total_files": len(files),
        "shared_precedent_total": len(shared_prec),
        "cross_book_precedent": len(cross_book_prec),
        "dup_candidate_total": len(dup_candidates),
        "cross_book_precedent_groups": cross_book_prec[:120],
        "dup_candidates": dup_candidates[:200],
        "cross_topic_keywords": cross_topic,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    L = []
    L.append("# v37 카드 간 관계(NLP) 분석 (2026-06-21)\n")
    L.append(f"- 카드 {len(cards)} · 파일 {len(files)}")
    L.append(f"- 같은 사건번호 공유 그룹 {len(shared_prec)} (그중 **2책 이상 교차 {len(cross_book_prec)}**)")
    L.append(f"- 중복 후보쌍(유사도≥0.55, 다른책) {len(dup_candidates)}\n")
    L.append("## 여러 책에 걸친 동일 판례 (상위 25)\n")
    L.append("| 사건번호 | 책수 | 카드수 | 책 |")
    L.append("|---|---:|---:|---|")
    for g in cross_book_prec[:25]:
        L.append(f"| {g['caseno']} | {g['n_books']} | {g['n_cards']} | {', '.join(g['books'])} |")
    L.append("")
    L.append("## 중복 후보쌍 (상위 25)\n")
    for d in dup_candidates[:25]:
        L.append(f"- ({d['sim']}) {d['a']}  ↔  {d['b']}  [공유 {d['shared_case']}]")
    L.append("")
    L.append("## 여러 책 공통 키워드(주제 연결고리, 상위 30)\n")
    L.append(", ".join(f"{k}({n})" for k, n in cross_topic[:30]))
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L))

    print(f"cards={len(cards)} shared_prec={len(shared_prec)} cross_book={len(cross_book_prec)} dup={len(dup_candidates)}")
    print(f"[written] {OUT_MD}")
    print(f"[written] {OUT_JSON}")


if __name__ == "__main__":
    main()
