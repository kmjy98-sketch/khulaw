# -*- coding: utf-8 -*-
"""
build_v37_tsv.py — outputs/02_cards_v37/*.md → Anki 임포트 TSV.
2026-06-25: apkg 빌더(build_v37_apkg)와 동기화 — deck_of(BOOK 단일출처)·blocks_of·field
재사용으로 책 매핑·블록 파싱·cloze/basic 판정을 apkg와 일치(누락 책·DOUBLE 카드 복구).
출력 차이는 형식만(genanki .apkg ↔ 텍스트 TSV). 주제:: 태그도 출력(apkg 정합).
출력: outputs/anki/v37/{덱}_basic.tsv / _cloze.tsv (+ _build_report.md). 비파괴.
파일럿: --limit N.
"""
import os
import re
import sys
import argparse
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import vp  # noqa: E402
import build_v37_apkg as B  # noqa: E402  # deck_of·blocks_of·field·헬퍼 단일출처

SRC = vp("outputs", "02_cards_v37")
OUT = vp("outputs", "anki", "v37")
DOUBLE = True  # 암기장: 빈칸 cloze + 완성문 Basic 둘 다(apkg와 동일)

_RE_NAN = re.compile(r"난이도::([ABab])")


def number_cloze(text):
    n = [0]
    def rep(m):
        inner = m.group(1)
        if re.match(r"\s*c\d+::", inner):
            return "{{" + inner + "}}"
        n[0] += 1
        return "{{c%d::%s}}" % (n[0], inner.strip())
    return re.sub(r"\{\{(.+?)\}\}", rep, text, flags=re.S)


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--limit", type=int, default=None, help="파일럿: 앞 N개 파일만")
    args = ap_.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.makedirs(OUT, exist_ok=True)
    basic = defaultdict(list)
    cloze = defaultdict(list)
    skipped = defaultdict(int)
    files = 0

    names = sorted(os.listdir(SRC))
    minso_cloze_pages = {re.search(r"_p[\d-]+", f).group(0) for f in names
                         if f.startswith("논점민소") and "_cloze" in f and re.search(r"_p[\d-]+", f)}
    if args.limit:
        names = names[:args.limit]

    for fn in names:
        if fn in ("H", "H:") or not fn.endswith(".md") or "_TEMP" in fn:
            skipped["junk"] += 1
            continue
        txt = open(os.path.join(SRC, fn), encoding="utf-8").read()
        if txt.count("\n") < 30:
            skipped["empty"] += 1
            continue
        if fn.startswith("논점민소") and "_cloze" not in fn:
            pg = re.search(r"_p[\d-]+", fn)
            if pg and pg.group(0) in minso_cloze_pages:
                skipped["논점민소구OX"] += 1
                continue
        grp, subj = B.deck_of(fn)
        if grp is None:
            skipped["미매핑:" + fn[:20]] += 1
            continue
        deck = f"{grp}::{subj}" if subj else grp
        bookkey = re.split(r"_p\d|_llamaparse", fn)[0]
        pages = (re.search(r"_p[\d-]+", fn) or [""])[0]
        out_src = f"{bookkey}{pages}".replace("_llamaparse", "")
        head_verify = re.findall(r"검증필요::\S+", txt[:400])
        files += 1

        for attr, topic, blk in B.blocks_of(txt):
            ap, dwi, bk, tx = (B.field(blk, ["앞", "앞면"]), B.field(blk, ["뒤", "뒷면"]),
                               B.field(blk, ["빈칸"]), B.field(blk, ["Text"]))
            tags = [f"과목::{subj or '기타'}", f"속성::{attr or '기타'}", f"출처::{out_src}"]
            nan = _RE_NAN.search(blk)
            if nan:
                tags.append(f"난이도::{nan.group(1).upper()}")
            if topic:
                tags.append(f"주제::{topic}")
            tags += head_verify
            tagstr = " ".join(dict.fromkeys(tags))
            cloze_src = next((x for x in (bk, tx, dwi, ap) if x and "{{" in x), "")
            head_front = re.sub(r"^#+\s*\[[^\]]*\]\s*", "", blk.split("\n", 1)[0]).strip()
            if cloze_src:
                t = number_cloze(B._fmt(cloze_src)) if hasattr(B, "_fmt") else number_cloze(cloze_src)
                if "{{c" in t:
                    extra = "" if (cloze_src == ap or (ap and "{{" in ap)) else ap
                    cloze[deck].append((t.replace("\t", " "), extra.replace("\t", " "), out_src, tagstr))
            want_basic = (not cloze_src and dwi and (ap or head_front)) or \
                         (DOUBLE and cloze_src == bk and bk and dwi and "{{" not in dwi)
            if want_basic:
                front = (ap or head_front).replace("\t", " ")
                back = dwi.replace("\t", " ")
                if front and back:
                    basic[deck].append((front, back, out_src, tagstr))

    for deck in sorted(set(basic) | set(cloze)):
        safe = deck.replace("::", "_")
        if basic[deck]:
            with open(f"{OUT}/{safe}_basic.tsv", "w", encoding="utf-8", newline="\n") as f:
                f.write("#separator:tab\n#html:true\n#deck:%s\n#columns:Front\tBack\t출처\tTags\n#tags column:4\n" % deck)
                for fr, b, s, tg in basic[deck]:
                    f.write(f"{fr}\t{b}\t{s}\t{tg}\n")
        if cloze[deck]:
            with open(f"{OUT}/{safe}_cloze.tsv", "w", encoding="utf-8", newline="\n") as f:
                f.write("#separator:tab\n#html:true\n#notetype:Cloze\n#deck:%s\n#columns:Text\tExtra\t출처\tTags\n#tags column:4\n" % deck)
                for t, ex, s, tg in cloze[deck]:
                    f.write(f"{t}\t{ex}\t{s}\t{tg}\n")

    tb = sum(len(v) for v in basic.values())
    tc = sum(len(v) for v in cloze.values())
    rep = ["# v37 TSV 빌드 리포트", f"- 처리 파일 {files} / Basic {tb} / Cloze {tc} / 합 {tb+tc}", "",
           "| 덱 | Basic | Cloze |", "|---|---:|---:|"]
    for d in sorted(set(basic) | set(cloze)):
        rep.append(f"| {d} | {len(basic[d])} | {len(cloze[d])} |")
    rep += ["", "- skip: " + ", ".join(f"{k}={v}" for k, v in sorted(skipped.items()))]
    open(f"{OUT}/_build_report.md", "w", encoding="utf-8").write("\n".join(rep))
    print("\n".join(rep[:6]))
    print("skip:", dict(skipped) if args.limit else sum(skipped.values()))


if __name__ == "__main__":
    main()
