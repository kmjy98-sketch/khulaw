#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v37 카드 클로즈/품질 전수 감사 (#08 빈칸기준 + cloze_integrity).
출력: 9.작업중/클로드/클로즈감사_2026-06-21.md + .agent/state/_cloze_audit_2026-06-21.json
빌더(build_v37_apkg.py)와 동일 파싱: 필드라벨 앞/앞면·뒤/뒷면·빈칸·Text, cloze {{c1::}}/bare {{}}.
"""
import os, re, json, sys, glob, html

CARD_DIR = r"H:\내 드라이브\outputs\02_cards_v37"
OUT_MD   = r"H:\내 드라이브\9.작업중/클로드\클로즈감사_2026-06-21.md"
OUT_JSON = r"H:\내 드라이브\.agent\state\_cloze_audit_2026-06-21.json"

CLOZE_RE = re.compile(r"\{\{\s*(?:c(\d+)\s*::)?\s*(.*?)\s*\}\}", re.S)
HEAD_RE  = re.compile(r"^(#{2,6})\s+(.*)$")
ATTR_RE  = re.compile(r"\[([^\]]+)\]")
JOMUN_RE = re.compile(r"제\s*\d+조(?:의\s*\d+)?")
CASE_RE  = re.compile(r"\d{2,4}(?:다|도|두|헌[가-힣]|가합|나|므|드|허|후|마|바|아|카)\w*\d+")

# 조사/연결어미 종결 — 파편 신호
JOSA_TAIL = ("을","를","이","가","은","는","의","에","와","과","도","로","으로","에서","에게","에는","까지","부터","마저","조차")
CONN_TAIL = ("관한","대한","위한","따른","인한","의한","관하여","대하여","위하여","통한","면서","므로","으로써","로써","고","며","하며","하고","하여","되어","에서의")

FIELD_FRONT = re.compile(r"^\s*(?:\*\*\s*)?(앞면?|앞)\s*(?:\*\*)?\s*[:：]?\s*(.*)$")
FIELD_BACK  = re.compile(r"^\s*(?:\*\*\s*)?(뒷면|뒤)\s*(?:\*\*)?\s*[:：]?\s*(.*)$")
FIELD_BLANK = re.compile(r"^\s*(?:\*\*\s*)?(빈칸)\s*(?:\*\*)?\s*[:：]?\s*(.*)$")


def split_cards(text):
    """헤딩(### 우선, ## 섹션은 컨텍스트) 기준으로 카드 블록 분할."""
    lines = text.split("\n")
    cards, cur, cur_head, cur_attr, section = [], [], None, None, None
    def flush():
        if cur_head is not None:
            cards.append({"head": cur_head, "attr": cur_attr, "section": section,
                          "body": "\n".join(cur)})
    for ln in lines:
        m = HEAD_RE.match(ln)
        if m:
            level, title = len(m.group(1)), m.group(2).strip()
            am = ATTR_RE.search(title)
            # ## (2단계) 중 [속성] 없는 건 섹션 컨텍스트로 취급
            if level == 2 and not am:
                flush(); cur, cur_head, cur_attr = [], None, None
                section = title
                continue
            flush()
            cur, cur_head = [], title
            cur_attr = am.group(1) if am else None
        else:
            if cur_head is not None:
                cur.append(ln)
    flush()
    return cards


def field_value(body, regex):
    """필드 라벨 줄 + (라벨 뒤 빈 경우) 다음 비어있지 않은 줄."""
    lines = body.split("\n")
    for i, ln in enumerate(lines):
        m = regex.match(ln)
        if m:
            val = m.group(2).strip()
            if val:
                return val
            for j in range(i+1, min(i+4, len(lines))):
                if lines[j].strip():
                    return lines[j].strip()
            return ""
    return None


def strip_markup(s):
    s = re.sub(r"\*\*|__|`", "", s)
    return s.strip()


def analyze_card(card, fname):
    body = card["body"]
    front = field_value(body, FIELD_FRONT)
    back  = field_value(body, FIELD_BACK)
    blank = field_value(body, FIELD_BLANK)
    attr  = card["attr"] or ""
    # cloze 수집 (back + blank + body 전반)
    clozes = CLOZE_RE.findall(body)  # [(num, content), ...]
    cloze_contents = [c.strip() for (_, c) in clozes]
    nums = [n for (n, _) in clozes if n]
    bare = sum(1 for (n, _) in clozes if not n)
    issues = []

    # 1) 빈칸 라벨은 있는데 본문 cloze 0 (실제 결함 — 빌더가 cloze 못 만듦)
    #    (Basic-by-design 카드[OX·사례A·C]는 빈칸라벨이 없으므로 자동 제외 → 오탐 없음)
    if blank is not None and len(clozes) == 0:
        issues.append("빈칸라벨_있으나_cloze0")

    # 2) 빈 클로즈
    if any(c == "" for c in cloze_contents):
        issues.append("빈_cloze")

    # 3) 개수 상한 (카드당 4 초과)
    if len(clozes) > 4:
        issues.append(f"cloze過다({len(clozes)})")

    # 4) 파편(조사/연결어미 종결)
    frag = []
    for c in cloze_contents:
        cc = strip_markup(c)
        if not cc:
            continue
        last = cc.split()[-1] if cc.split() else cc
        if cc.endswith(JOSA_TAIL) or cc.endswith(CONN_TAIL):
            frag.append(cc[:18])
    if frag:
        issues.append("파편_조사연결어종결:" + " / ".join(frag[:3]))

    # 5) anchor(조문/사건번호)를 cloze 안에 넣음
    anch = []
    for c in cloze_contents:
        if JOMUN_RE.search(c) or CASE_RE.search(c):
            anch.append(strip_markup(c)[:20])
    if anch:
        issues.append("anchor_cloze:" + " / ".join(anch[:3]))

    # 6) 누설: cloze 내용이 같은 카드의 '뒤' cloze 밖에 그대로 등장
    #    (빈칸 답안줄·앞면 줄은 제외 — 답안키 재기재는 정상 관행이라 오탐 차단)
    kept = [ln for ln in body.split("\n")
            if not FIELD_BLANK.match(ln) and not FIELD_FRONT.match(ln)]
    outside = CLOZE_RE.sub(" ", "\n".join(kept))
    leaks = []
    for c in cloze_contents:
        cc = strip_markup(c)
        if len(cc) >= 4 and cc in outside:
            leaks.append(cc[:18])
    if leaks:
        issues.append("누설:" + " / ".join(leaks[:3]))

    # 7) 번호 연속성(번호 있는 경우)
    if nums:
        ns = sorted(set(int(n) for n in nums))
        if ns and ns != list(range(1, len(ns)+1)):
            issues.append(f"cloze번호_불연속({','.join(map(str,ns))})")

    # 8) 뒷면 누락 — ### [속성] 카드인데 앞면만 있고 뒤·cloze 모두 없음
    if attr and front is not None and back is None and len(clozes) == 0:
        issues.append("뒷면_없음")

    return {
        "file": fname, "head": card["head"], "attr": attr, "section": card["section"],
        "front": (front or "")[:60], "n_cloze": len(clozes), "bare": bare,
        "cloze_sample": cloze_contents[:4], "issues": issues,
    }


def main():
    files = sorted(glob.glob(os.path.join(CARD_DIR, "*.md")))
    all_cards, flagged = [], []
    by_file = {}
    front_index = {}
    for fp in files:
        fname = os.path.basename(fp)
        try:
            with open(fp, encoding="utf-8") as f:
                txt = f.read()
        except Exception as ex:
            continue
        cards = split_cards(txt)
        fstats = {"file": fname, "n_cards": 0, "n_flagged": 0, "issue_types": {}}
        for c in cards:
            a = analyze_card(c, fname)
            if not a["head"]:
                continue
            all_cards.append(a)
            fstats["n_cards"] += 1
            # 중복 앞면 인덱스
            fr = strip_markup(a["front"])
            if len(fr) >= 6:
                front_index.setdefault(fr, []).append(fname + " :: " + a["head"][:40])
            if a["issues"]:
                fstats["n_flagged"] += 1
                flagged.append(a)
                for iss in a["issues"]:
                    key = iss.split(":")[0].split("(")[0]
                    fstats["issue_types"][key] = fstats["issue_types"].get(key, 0) + 1
        by_file[fname] = fstats

    # 중복 앞면(서로 다른 카드/파일)
    dup_fronts = {k: v for k, v in front_index.items() if len(v) > 1}

    # 집계
    issue_totals = {}
    for a in flagged:
        for iss in a["issues"]:
            key = iss.split(":")[0].split("(")[0]
            issue_totals[key] = issue_totals.get(key, 0) + 1

    report = {
        "total_files": len(files), "total_cards": len(all_cards),
        "flagged_cards": len(flagged), "issue_totals": issue_totals,
        "dup_front_groups": len(dup_fronts),
        "by_file": by_file, "flagged": flagged,
        "dup_fronts": {k: v for k, v in list(dup_fronts.items())[:200]},
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    L = []
    L.append("# v37 카드 클로즈/품질 전수 감사 (2026-06-21)\n")
    L.append(f"- 파일 {len(files)} · 카드 {len(all_cards)} · 문제카드 {len(flagged)} ({len(flagged)*100//max(1,len(all_cards))}%)\n")
    L.append("## 문제 유형별 건수\n")
    for k, v in sorted(issue_totals.items(), key=lambda x:-x[1]):
        L.append(f"- {k}: {v}")
    L.append("")
    L.append(f"## 중복 앞면 후보 그룹: {len(dup_fronts)} (서로 다른 카드가 동일 질문)\n")
    L.append("## 파일별 문제카드 수 (상위 30)\n")
    L.append("| 파일 | 카드 | 문제 | 주요유형 |")
    L.append("|---|---:|---:|---|")
    rows = sorted(by_file.values(), key=lambda x:-x["n_flagged"])[:30]
    for r in rows:
        tt = ", ".join(f"{k}{v}" for k, v in sorted(r["issue_types"].items(), key=lambda x:-x[1])[:3])
        L.append(f"| {r['file']} | {r['n_cards']} | {r['n_flagged']} | {tt} |")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L))

    print(f"files={len(files)} cards={len(all_cards)} flagged={len(flagged)}")
    print("issue_totals=", json.dumps(issue_totals, ensure_ascii=False))
    print(f"[written] {OUT_MD}")
    print(f"[written] {OUT_JSON}")


if __name__ == "__main__":
    main()
