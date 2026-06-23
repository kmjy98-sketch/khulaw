# -*- coding: utf-8 -*-
"""
build_v37_tsv.py — outputs/02_cards_v37/*.md(검토용 readable) → Anki 임포트 TSV.
두 포맷 흡수: 사례형(뒤:에 {{c1::}}) + 암기장(앞/뒤/빈칸, 빈칸은 {{내용}} bare).
처리: cloze 번호 부여({{X}}→{{cN::X}}) · 한자→한글 · **볼드**→<b> · 덱/태그 · dedup/junk skip.
출력: outputs/anki/v37/{덱}_basic.tsv / _cloze.tsv (+ _build_report.md). 비파괴(원본 md 유지).
"""
import os, re, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

SRC = vp("outputs", "02_cards_v37")
OUT = vp("outputs", "anki", "v37")

# 책 prefix → (회독그룹, 과목). 교수저 제외. 논점민소는 cloze본만 사용.
BOOK = [
    ("민사사례연습1", "암기장-사례형", "민법"), ("사례연습_", "암기장-사례형", "민법"),
    ("작은변사기", "암기장-사례형", "형법"), ("해커스헌법사례", "암기장-사례형", "헌법"),
    ("논점민법재산법", "기본서", "민법"), ("논점민소", "기본서", "민사소송법"),
    ("반반형법", "암기장-객관식", "형법"), ("compact형총OX", "암기장-객관식", "형법"),
    ("쟁점노트_재산법", "암기장-객관식", "민법"), ("신민사", "암기장-객관식", "민법"),
    ("강성민OX", "암기장-객관식", "헌법"), ("유니온헌법기출", "암기장-객관식", "헌법"),
    ("헌법핵심정리300", "암기장-객관식", "헌법"), ("찌라시", "찌라시", None),
]
# 속성 태그(블록 헤더 → 속성)
ATTR = {"쟁점도출": "사례쟁점", "포섭": "포섭", "함정": "함정", "기재례": "기재례",
        "일반론": "일반론", "예외": "예외", "요건": "요건", "OX": "OX", "판례": "판례"}

HANJA = {"甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무", "己": "기", "庚": "경",
         "辛": "신", "壬": "임", "癸": "계", "條": "조", "項": "항", "號": "호", "判": "판",
         "債": "채", "權": "권", "物": "물", "者": "자", "前": "전", "後": "후", "相": "상",
         "他": "타", "本": "본", "等": "등", "及": "급", "又": "우", "因": "인", "故": "고"}


def deci(name):
    for p, g, s in BOOK:
        if name.startswith(p):
            return g, s
    return None, None


def hanja(t):
    return "".join(HANJA.get(c, c) for c in t)


def fmt(t):
    t = hanja(t).strip()
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return t.replace("\t", " ")


def number_cloze(text):
    """bare {{X}} → {{cN::X}} 순차. 이미 cN:: 있으면 유지."""
    n = [0]
    def rep(m):
        inner = m.group(1)
        if re.match(r"\s*c\d+::", inner):
            return "{{" + inner + "}}"
        n[0] += 1
        return "{{c%d::%s}}" % (n[0], inner.strip())
    return re.sub(r"\{\{(.+?)\}\}", rep, text, flags=re.S)


def field(block, key):
    m = re.search(rf"(?m)^\s*{key}\s*[:：]\s*(.*?)(?=(?:\n\s*(?:앞|뒤|빈칸|Text)\s*[:：])|\Z)", block, re.S)
    return m.group(1).strip() if m else ""


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.makedirs(OUT, exist_ok=True)
    basic = defaultdict(list); cloze = defaultdict(list)
    skipped = []; unparsed = 0; files = 0
    seen_minso_cloze = set(re.findall(r"논점민소(_p[\d-]+)_cloze", " ".join(os.listdir(SRC))))

    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".md"):
            if fn in ("H", "H:"):
                skipped.append((fn, "junk"))
            continue
        path = os.path.join(SRC, fn)
        txt = open(path, encoding="utf-8").read()
        if txt.count("\n") < 30:
            skipped.append((fn, "empty")); continue
        # dedup: 구 논점민소 OX(암기장) — cloze본 있으면 skip
        if fn.startswith("논점민소") and "_cloze" not in fn:
            pg = re.search(r"_p[\d-]+", fn)
            if pg and pg.group(0) in seen_minso_cloze:
                skipped.append((fn, "논점민소 구OX→cloze대체")); continue
        # dedup: 강성민OX3 등 _llamaparse 유무 중복 — 더 큰 파일 우선(여기선 단순히 둘 다 처리, 빌드 후 중복은 GUID로)
        grp, subj = deci(fn)
        if grp is None:
            skipped.append((fn, "미매핑")); continue
        src = re.search(r"(?m)^source:\s*(.+)$|범위:\s*(.+)$", txt)
        pages = (re.search(r"_p[\d-]+", fn) or [""])[0]
        deck = f"{grp}::{subj}" if subj else grp
        bookkey = re.split(r"_p\d|_llamaparse", fn)[0]
        out_src = f"{bookkey}{pages}".replace("_llamaparse", "")
        # 블록 분할
        blocks = re.split(r"(?m)^#{2,3}\s+", txt)
        for blk in blocks:
            head = blk.split("\n", 1)[0]
            attr = next((v for k, v in ATTR.items() if k in head or k in blk[:80]), "")
            tags = f"과목::{subj or '기타'} 속성::{attr or '기타'} 출처::{out_src}"
            ap, dwi, bk = field(blk, "앞"), field(blk, "뒤"), field(blk, "빈칸")
            text_field = field(blk, "Text")
            cl = bk or text_field or (dwi if "{{" in dwi else "")
            if cl and "{{" in cl:
                t = number_cloze(fmt(cl))
                if ap and "{{" not in ap:
                    t = fmt(ap) + "<br>" + t
                cloze[deck].append((t, out_src, tags))
            elif ap and dwi:
                basic[deck].append((fmt(ap), fmt(dwi), out_src, tags))
            elif blk.strip() and head and not blk.startswith(("사례", "[")):
                pass
        files += 1

    for deck in sorted(set(basic) | set(cloze)):
        safe = deck.replace("::", "_")
        if basic[deck]:
            with open(f"{OUT}/{safe}_basic.tsv", "w", encoding="utf-8", newline="\n") as f:
                f.write("#separator:tab\n#html:true\n#deck:%s\n#columns:Front\tBack\t출처\tTags\n#tags column:4\n" % deck)
                for fr, b, s, tg in basic[deck]:
                    f.write(f"{fr}\t{b}\t{s}\t{tg}\n")
        if cloze[deck]:
            with open(f"{OUT}/{safe}_cloze.tsv", "w", encoding="utf-8", newline="\n") as f:
                f.write("#separator:tab\n#html:true\n#notetype:Cloze\n#deck:%s\n#columns:Text\t출처\tTags\n#tags column:3\n" % deck)
                for t, s, tg in cloze[deck]:
                    f.write(f"{t}\t{s}\t{tg}\n")

    tb = sum(len(v) for v in basic.values()); tc = sum(len(v) for v in cloze.values())
    rep = [f"# v37 TSV 빌드 리포트", f"- 처리 파일 {files} / Basic {tb} / Cloze {tc} / 합 {tb+tc}", "",
           "| 덱 | Basic | Cloze |", "|---|---:|---:|"]
    for d in sorted(set(basic) | set(cloze)):
        rep.append(f"| {d} | {len(basic[d])} | {len(cloze[d])} |")
    rep += ["", f"- skip {len(skipped)}건:"] + [f"  - {n} ({why})" for n, why in skipped[:40]]
    open(f"{OUT}/_build_report.md", "w", encoding="utf-8").write("\n".join(rep))
    print("\n".join(rep[:6]))
    print("skip:", len(skipped))


if __name__ == "__main__":
    main()
