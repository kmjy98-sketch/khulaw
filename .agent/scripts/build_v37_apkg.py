# -*- coding: utf-8 -*-
"""
build_v37_apkg.py — outputs/02_cards_v37/*.md(3포맷) → genanki 과목별 .apkg.
포맷 통합 파서: 블록(### 또는 **카드) 단위로 앞/뒤/빈칸/Text 추출 → Basic/Cloze 생성.
- 암기장 빈칸(bare {{}}) → cloze 번호부여 + 완성문 Basic 동시(double).
- 사례형/논점민소 뒤:{{cN::}} → Cloze.
- 한자→한글(hanja.translate) · **볼드**→<b> · 경계 트림 · dedup/junk/empty skip.
- 덱=회독그룹::과목, 태그=과목/속성/출처/회독그룹, GUID=출처+헤더+본문(재임포트 회독보존).
- 출력: outputs/anki/v37/apkg/{과목}_v37.apkg + _apkg_report.md. 비파괴.
"""
import os, re, sys, hashlib, html
from collections import defaultdict
import genanki
from hanja import translate as h2k
from _guid_stable import guid_seed, extract_uid  # 안정 note_key guid (card-wiki-pipeline §8.1)

SRC = "H:/내 드라이브/outputs/02_cards_v37"
OUT = "H:/내 드라이브/outputs/anki/v37/apkg"
DOUBLE = True  # 암기장: 완성문 Basic + cloze 둘 다 (사용자 선택)

BOOK = [  # prefix → (회독그룹, 과목)
    ("민사사례연습1", "암기장-사례형", "민법"), ("사례연습_", "암기장-사례형", "민법"),
    ("작은변사기", "암기장-사례형", "형법"), ("해커스헌법사례", "암기장-사례형", "헌법"),
    ("논점민법재산법", "기본서", "민법"), ("논점민소", "기본서", "민사소송법"),
    ("김기용형총", "기본서", "형법"),
    ("반반형법", "암기장-객관식", "형법"), ("compact형총OX", "암기장-객관식", "형법"),
    ("쟁점노트_재산법", "암기장-객관식", "민법"), ("신민사", "암기장-객관식", "민법"),
    ("강성민OX", "암기장-객관식", "헌법"), ("유니온헌법기출", "암기장-객관식", "헌법"),
    ("헌법핵심정리300", "암기장-객관식", "헌법"),
]
CHIRASHI = {"민법": "민법", "민사소송법": "민사소송법", "형법": "형법", "형사소송법": "형사소송법",
            "헌법": "헌법", "상법": "상법", "행정법": "행정법"}
ATTR = [("쟁점도출", "사례쟁점"), ("포섭", "포섭"), ("함정", "함정"), ("기재례", "기재례"),
        ("일반론", "일반론"), ("예외", "예외"), ("요건", "요건"), ("OX", "OX"), ("판례", "판례")]
ENDI = ("므로", "하여", "하면서", "한바", "으며", "이며", "거나", "면서", "는데", "는바", "어서", "지만")
GWAN = ("관한", "대한", "위한", "따른", "인한", "관하여", "대하여", "있어서")
CJK = re.compile(r"[一-鿿]")

CSS = (".card{font-family:'Malgun Gothic','Noto Sans KR',sans-serif;font-size:18px;"
       "line-height:1.7;text-align:left;color:#1a1a1a}.cloze{color:#0b66c3;font-weight:700}"
       "b{color:#c0392b}.extra{color:#666;font-size:15px}.src{color:#999;font-size:13px}"
       "table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:3px 7px}")
BASIC = genanki.Model(1737420001, "v37 Basic", fields=[{"name": "Front"}, {"name": "Back"}, {"name": "출처"}],
                      templates=[{"name": "C", "qfmt": "{{Front}}", "afmt": "{{FrontSide}}<hr id=answer>{{Back}}<br><span class=src>{{출처}}</span>"}], css=CSS)
CLOZE = genanki.Model(1737420002, "v37 Cloze", model_type=genanki.Model.CLOZE,
                      fields=[{"name": "Text"}, {"name": "Extra"}, {"name": "출처"}],
                      templates=[{"name": "C", "qfmt": "{{cloze:Text}}<br><span class=extra>{{Extra}}</span>",
                                  "afmt": "{{cloze:Text}}<br><span class=extra>{{Extra}}</span><hr><span class=src>{{출처}}</span>"}], css=CSS)


def did(name):
    return int(hashlib.md5(name.encode()).hexdigest()[:9], 16)


def conv(t):
    if not t:
        return ""
    t = h2k(t, "substitution")
    t = html.escape(t, quote=False)            # 법률 텍스트의 < > & 이스케이프
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)  # 그 후 볼드만 실제 태그로
    return t.strip()


def number_cloze(text):
    n = [0]
    def rep(m):
        inner = m.group(1)
        if re.match(r"\s*c\d+::", inner):
            return "{{" + inner + "}}"
        n[0] += 1
        return "{{c%d::%s}}" % (n[0], inner.strip())
    return re.sub(r"\{\{(.+?)\}\}", rep, text, flags=re.S)


def trim_blank(text):
    def rep(m):
        idx, c = m.group(1), m.group(2)
        w = c.strip().split()
        while w and (w[-1] in GWAN or any(w[-1].endswith(e) for e in ENDI)
                     or (len(w[-1]) >= 2 and w[-1][-1] in "을를")):
            w.pop()
        return "{{c%s::%s}}" % (idx, " ".join(w) if w else c.strip())
    return re.sub(r"\{\{c(\d+)::(.*?)\}\}", rep, text, flags=re.S)


def attr_of(s):
    for k, v in ATTR:
        if k in s:
            return v
    return ""


def deck_of(fn):
    if fn.startswith("찌라시"):
        m = re.search(r"찌라시_([^_]+)_", fn)
        subj = m.group(1) if m and m.group(1) in CHIRASHI else "기타"
        return "찌라시", subj
    for p, g, s in BOOK:
        if fn.startswith(p):
            return g, s
    return None, None


_LABELS = r"(?:앞면|뒷면|빈칸|앞|뒤|Text|태그)"

def field(block, keys):
    # 라벨 변형 흡수: 앞|앞면, 뒤|뒷면. **라벨** / 라벨: / **라벨**\n내용 (콜론선택, 내용 다음줄 허용)
    alt = "|".join(keys)
    pat = (rf"\*{{0,2}}\s*(?:{alt})\s*\*{{0,2}}\s*[:：]?\s*"
           rf"(.*?)(?=\n\s*\*{{0,2}}\s*{_LABELS}\s*\*{{0,2}}\s*[:：]?|\Z)")
    m = re.search(pat, block, re.S)
    return m.group(1).strip(" *\n\t") if m else ""


def blocks_of(txt):
    """### 또는 **카드 단위로 분할. 속성은 블록헤더 우선, 없으면 직전 ## 헤더."""
    out = []
    cur = None
    h2attr = ""
    for ln in txt.split("\n"):
        is_h = re.match(r"^#{2,6}\s", ln)
        if is_h or re.match(r"^\s*\*{0,2}\s*카드\s*[\dA-Za-z]", ln):
            if cur:
                out.append(cur)
            a = attr_of(ln)
            if ln.startswith("## ") and not ln.startswith("###"):
                h2attr = a            # h2 헤더는 컨텍스트(하위 **카드** attr)도 갱신
            cur = [a or h2attr, ln + "\n"]
        elif cur:
            cur[1] += ln + "\n"
    if cur:
        out.append(cur)
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.makedirs(OUT, exist_ok=True)
    files = os.listdir(SRC)
    minso_cloze_pages = {re.search(r"_p[\d-]+", f).group(0) for f in files
                         if f.startswith("논점민소") and "_cloze" in f and re.search(r"_p[\d-]+", f)}
    decks = {}            # deckname -> Deck
    subj_decks = defaultdict(set)  # 과목 -> {deckname}
    seen = set()
    cnt = defaultdict(lambda: [0, 0])  # deckname -> [basic, cloze]
    skipped = defaultdict(int)
    n_basic = n_cloze = 0

    def get_deck(name):
        if name not in decks:
            decks[name] = genanki.Deck(did(name), name)
        return decks[name]

    for fn in sorted(files):
        if fn in ("H", "H:") or not fn.endswith(".md") or "_TEMP" in fn:
            skipped["junk"] += 1; continue
        path = os.path.join(SRC, fn)
        txt = open(path, encoding="utf-8").read()
        if txt.count("\n") < 30:
            skipped["empty"] += 1; continue
        if fn.startswith("논점민소") and "_cloze" not in fn:
            pg = re.search(r"_p[\d-]+", fn)
            if pg and pg.group(0) in minso_cloze_pages:
                skipped["논점민소구OX"] += 1; continue
        grp, subj = deck_of(fn)
        if grp is None:
            skipped["미매핑:" + fn[:20]] += 1; continue
        deckname = f"{grp}::{subj}"
        bookkey = re.split(r"_p\d|_llamaparse", fn)[0]
        pages = (re.search(r"_p[\d-]+", fn) or [""])[0]
        src = f"{bookkey}{pages}".replace("_llamaparse", "")
        stem = fn[:-3] if fn.endswith(".md") else fn   # note_key용 파일 stem (§8.1)
        seq = 0                                          # 파일내 카드 순번(내용 비의존)

        for attr, blk in blocks_of(txt):
            ap, dwi, bk, tx = field(blk, ["앞", "앞면"]), field(blk, ["뒤", "뒷면"]), field(blk, ["빈칸"]), field(blk, ["Text"])
            cloze_src = next((x for x in (bk, tx, dwi, ap) if x and "{{" in x), "")  # 앞(cloze): 흡수
            if not cloze_src and "{{" in blk and not (ap and "{{" in ap):
                body = blk.split("\n", 1)[1] if "\n" in blk else ""
                cloze_src = re.sub(r"(?m)^\s*\*{0,2}\s*카드\s*[\w-]*\s*\*{0,2}\s*", "", body).strip()
            tags = [f"과목::{subj}", f"속성::{attr or '기타'}", f"출처::{src}", f"회독그룹::{grp}"]
            made = False
            if cloze_src:
                ctext = trim_blank(number_cloze(conv(cloze_src)))
                if "{{c" in ctext and not re.search(r"\{\{(?!c\d+::)", ctext):
                    g = genanki.guid_for(guid_seed(stem, "cloze", seq, explicit_uid=extract_uid(blk)))
                    seq += 1
                    dkey = ("C", src, re.sub(r"\s+", "", ctext))  # 내용 dedup은 guid와 분리(§8.1)
                    extra = "" if (cloze_src == ap or (ap and "{{" in ap)) else conv(ap)
                    nt = genanki.Note(model=CLOZE, fields=[ctext, extra, src], guid=g, tags=tags)
                    if dkey not in seen:
                        seen.add(dkey); get_deck(deckname).add_note(nt)
                        subj_decks[subj].add(deckname); cnt[deckname][1] += 1; n_cloze += 1
                    made = True
            # Basic: 앞+뒤 / [OX-N] 선지=헤더+뒤만 / double(빈칸 cloze+완성문)
            head_front = re.sub(r"^\*+\s*카드\s*[\w-]*\s*\*+\s*", "",
                                re.sub(r"^#+\s*\[[^\]]*\]\s*", "", blk.split("\n", 1)[0])).strip()
            want_basic = (not cloze_src and dwi and (ap or head_front)) or (DOUBLE and cloze_src == bk and bk and dwi and "{{" not in dwi)
            if want_basic:
                front = conv(ap) or conv(head_front) or attr
                back = conv(dwi)
                if front and back:
                    g = genanki.guid_for(guid_seed(stem, "basic", seq, explicit_uid=extract_uid(blk)))
                    seq += 1
                    dkey = ("B", src, re.sub(r"\s+", "", front + back))  # 내용 dedup은 guid와 분리(§8.1)
                    nt = genanki.Note(model=BASIC, fields=[front, back, src], guid=g, tags=tags)
                    if dkey not in seen:
                        seen.add(dkey); get_deck(deckname).add_note(nt)
                        subj_decks[subj].add(deckname); cnt[deckname][0] += 1; n_basic += 1
                    made = True

    # 과목 × 책종류(회독그룹) 분할: outputs/anki/v37/apkg/{과목}/{회독그룹}_v37.apkg
    n_files = 0
    for deckname in sorted(decks):
        grp, subj = (deckname.split("::") + [""])[:2]
        sub = os.path.join(OUT, subj)
        os.makedirs(sub, exist_ok=True)
        genanki.Package([decks[deckname]]).write_to_file(os.path.join(sub, f"{grp}_v37.apkg"))
        n_files += 1

    # 검증
    rep = ["# v37 apkg 빌드 리포트", f"- Basic {n_basic} / Cloze {n_cloze} / 합 {n_basic + n_cloze}",
           f"- apkg {n_files}개 (과목×책종류 분할): {len(subj_decks)}과목 × 책종류별 → outputs/anki/v37/apkg/{{과목}}/{{회독그룹}}_v37.apkg", "",
           "| 덱 | Basic | Cloze |", "|---|---:|---:|"]
    for d in sorted(cnt):
        rep.append(f"| {d} | {cnt[d][0]} | {cnt[d][1]} |")
    rep.append("")
    rep.append("- skip: " + ", ".join(f"{k}={v}" for k, v in skipped.items()))
    open(f"{OUT}/_apkg_report.md", "w", encoding="utf-8").write("\n".join(rep))
    print("\n".join(rep[:6]))
    print("skip:", dict(skipped))


if __name__ == "__main__":
    main()
