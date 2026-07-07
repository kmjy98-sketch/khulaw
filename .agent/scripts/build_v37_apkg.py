# -*- coding: utf-8 -*-
"""
build_v37_apkg.py — outputs/02_cards_v37/*.md(3포맷) → genanki 과목별 .apkg.
포맷 통합 파서: 블록(### 또는 **카드) 단위로 앞/뒤/빈칸/Text 추출 → Basic/Cloze 생성.
- 암기장 빈칸(bare {{}}) → cloze 번호부여 + 완성문 Basic 동시(double).
- 사례형/논점민소 뒤:{{cN::}} → Cloze.
- 한자→한글(hanja.translate)·不 활음조보정 · **볼드**→<b> · 표→<table> · 색상강조(사건번호 cn/조문 law/결론 vd/열거 en) · 답면 노랑형광(per-card LLM 캐시 우선·어휘 폴백)
  · 공백 뒤 열거마커(①~⑳·㉠~㉭) 앞 <br>(붙은 참조 §444① 제외) · 경계 트림 · dedup/junk/empty skip.
- 덱=회독그룹::과목, 태그=과목/속성/출처/회독그룹 + 난이도::(명시 카드)·주제::(## [주제] 헤더)·기출::([변/모/입N] 마커)·검증필요::(파일머리).
- GUID=안정 note_key({파일stem}::{basic|cloze}::{헤더소제목}::{occ:02d})에서 파생 → 카드 텍스트 수정해도 guid 유지
  → 재임포트 시 동일 노트 업데이트(FSRS/복습이력 보존). 헤더(소제목) 앵커라 재정렬·삽입에도 안정(같은 헤더 중복만 occ로 구분).
  내용기반 dedup(seen)은 별도 유지해 총장수 보존.
- 출력: outputs/anki/v37/apkg/{과목}_v37.apkg + _apkg_report.md. 비파괴.
"""
import os, re, sys, hashlib, html
from collections import defaultdict
import genanki
from hanja import translate as h2k
from _guid_stable import guid_seed, extract_uid  # 안정 note_key guid (card-wiki-pipeline §8.1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _vault import VAULT_ROOT, vp  # noqa: E402

SRC = os.environ.get("V37_SRC", vp("outputs", "02_cards_v37"))        # 테스트 env 오버라이드, 기본 VAULT_ROOT(E:)
OUT = os.environ.get("V37_OUT", vp("outputs", "anki", "v37", "apkg"))
DOUBLE = True  # 암기장: 완성문 Basic + cloze 둘 다 (사용자 선택)

BOOK = [  # prefix → (회독그룹, 과목)
    ("민사사례연습1", "암기장-사례형", "민법"), ("사례연습_", "암기장-사례형", "민법"),
    ("민소사례", "암기장-사례형", "민사소송법"),
    ("작은변사기", "암기장-사례형", "형법"), ("해커스헌법사례", "암기장-사례형", "헌법"),
    ("논점민법재산법", "기본서", "민법"), ("논점민소", "기본서", "민사소송법"),
    ("김기용형총", "기본서", "형법"),
    ("반반형법", "암기장-객관식", "형법"), ("compact형총OX", "암기장-객관식", "형법"),
    ("쟁점노트_재산법", "암기장-객관식", "민법"), ("신민사", "암기장-객관식", "민법"),
    ("쟁점노트_소송집행", "암기장-객관식", "민사소송법"),
    ("쟁점노트_가족법", "암기장-객관식", "민법"),
    ("기초법리집행법", "기본서", "민사집행법"),
    ("강성민OX", "암기장-객관식", "헌법"), ("유니온헌법기출", "암기장-객관식", "헌법"),
    ("헌법핵심정리300", "암기장-객관식", "헌법"),
    ("행정법강해", "기본서", "행정법"),
    ("법조윤리", "암기장-객관식", "법조윤리"),
]
CHIRASHI = {"민법": "민법", "민사소송법": "민사소송법", "형법": "형법", "형사소송법": "형사소송법",
            "헌법": "헌법", "상법": "상법", "행정법": "행정법"}
ATTR = [("쟁점도출", "사례쟁점"), ("포섭", "포섭"), ("함정", "함정"), ("기재례", "기재례"),
        ("일반론", "일반론"), ("예외", "예외"), ("요건", "요건"), ("학설", "학설"), ("OX", "OX"), ("판례", "판례")]
ENDI = ("므로", "하여", "하면서", "한바", "으며", "이며", "거나", "면서", "는데", "는바", "어서", "지만")
GWAN = ("관한", "대한", "위한", "따른", "인한", "관하여", "대하여", "있어서")
CJK = re.compile(r"[一-鿿]")

CSS = (".card{font-family:'Malgun Gothic','Noto Sans KR',sans-serif;font-size:18px;"
       "line-height:1.7;text-align:left;color:#1a1a1a}.cloze{color:#0b66c3;font-weight:700}"
       "b{color:#c0392b}.extra{color:#666;font-size:15px}.src{color:#999;font-size:13px}"
       "table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:3px 7px}"
       ".cn{color:#2e86d1}.law{color:#1a9a55}.vd{color:#e5484d;font-weight:700}"
       ".en{color:#d97706;font-weight:700}.hl{background:#a5d8ff;color:#0b2e4f;border-radius:3px}")
BASIC = genanki.Model(1737420001, "v37 Basic", fields=[{"name": "Front"}, {"name": "Back"}, {"name": "출처"}],
                      templates=[{"name": "C", "qfmt": "{{Front}}", "afmt": "{{FrontSide}}<hr id=answer>{{Back}}<br><span class=src>{{출처}}</span>"}], css=CSS)
CLOZE = genanki.Model(1737420002, "v37 Cloze", model_type=genanki.Model.CLOZE,
                      fields=[{"name": "Text"}, {"name": "Extra"}, {"name": "출처"}],
                      templates=[{"name": "C", "qfmt": "{{cloze:Text}}<br><span class=extra>{{Extra}}</span>",
                                  "afmt": "{{cloze:Text}}<br><span class=extra>{{Extra}}</span><hr><span class=src>{{출처}}</span>"}], css=CSS)


def did(name):
    return int(hashlib.md5(name.encode()).hexdigest()[:9], 16)


_CHO_BU = (3, 4, 12, 13)  # 초성 ㄷㄸㅈㅉ — 不 뒤 활음조 → '부'


def _bu_bul(t):
    # 不(부/불) 활음조 보정: 다음 음절 초성이 ㄷ/ㅈ계열이면 '부', 아니면 '불'.
    # h2k가 不을 항상 '불'로 바꾸는 오변환(不正→불정, 不知→불지) 교정. anchor(조문·사건번호) 무관.
    def rep(m):
        nxt = m.group(1)
        r = h2k(nxt, "substitution") if "一" <= nxt <= "鿿" else nxt
        if r and "가" <= r[0] <= "힣" and ((ord(r[0]) - 0xAC00) // 588) in _CHO_BU:
            return "부" + nxt
        return "불" + nxt
    return re.sub(r"不([가-힣一-鿿])", rep, t)


# 색상 강조 (CSS 클래스: cn 사건번호 / law 조문 / vd 결론어 / en 열거마커)
_VERD = ("무효", "위헌", "합헌", "각하", "기각", "인용", "파기", "유죄", "무죄",
         "적법", "위법", "불성립", "추정", "간주", "의제")
_CASE_CODE = (r"헌가|헌마|헌바|헌라|헌나|헌사|헌아|민상|형상|고합|고단|고정|가합|가단|다카|"
              r"다|도|두|마|머|모|므|르|즈|후|허|노|오|초|보|감|구|누|부|추|그|나|라|카")
_RE_CASE = re.compile(r"(\d{2,4}(?:" + _CASE_CODE + r")\d{1,6})")  # 64민상9·2009다100096·2019헌가3 (날짜·계수 제외)
_RE_LAW = re.compile(r"(§\s*\d+(?:의\s*\d+)?|제\s*\d+\s*조(?:의\s*\d+)?)")
_RE_VERD = re.compile("(" + "|".join(_VERD) + ")")
_RE_ENUM = re.compile(r"\s+([①-⑳㉠-㉭])")       # 공백 뒤 ①~⑳·㉠~㉭ (붙은 참조 제외)
# 난이도 메타: 난이도: A / 난이도 B / [난이도 A] / (난이도 B) (인라인 포함, 한 줄 내). 등급은 A~C만 실측.
_RE_NAN = re.compile(r"[ \t]*[\[(]?[ \t]*난이도[ \t]*[:：]?[ \t]*([A-Ca-c])[ \t]*[\])]?")


# 노랑 형광(Basic 답면): per-card LLM 캐시(anki_v37_hl_cache.jsonl, 답면별 정밀 키워드) 우선,
# 없으면 개념어 사전(anki_concept_vocab.txt, v4.2 캐시 정제·빈도≥5) 어휘 폴백. 둘 다 없으면 비활성.
try:
    _HLVOCAB = sorted((w.strip() for w in open(vp(".agent", "state", "anki_concept_vocab.txt"),
                       encoding="utf-8").read().split("\n") if len(w.strip()) >= 3), key=len, reverse=True)
except OSError:
    _HLVOCAB = []

# per-card 정밀 캐시(md5(_base(답면)) → [키워드]). LLM 추출본. 있으면 어휘판보다 우선.
try:
    import json as _json
    _HLCACHE = {_d["k"]: _d["kw"] for _d in
                (_json.loads(_l) for _l in open(vp(".agent", "state", "anki_v37_hl_cache.jsonl"),
                 encoding="utf-8") if _l.strip())}
except OSError:
    _HLCACHE = {}


def _highlight(t, cap=2, kws=None):
    # 답면 형광: per-card kws(부분문자열 검증) 우선, 없으면 개념어 사전 폴백. 태그 내부·겹침 회피.
    if kws:
        terms = sorted({k.strip() for k in kws if k and k.strip() in t}, key=len, reverse=True)
        lim = min(len(terms), 4)
    else:
        terms = _HLVOCAB
        lim = cap
    if not terms:
        return t
    found = []
    for term in terms:
        if len(found) >= lim:
            break
        i = t.find(term)
        if i < 0:
            continue
        if t.rfind("<", 0, i) > t.rfind(">", 0, i):   # 태그 속이면 skip
            continue
        e = i + len(term)
        if any(i < fe and e > fs for fs, fe in found):  # 겹침 skip
            continue
        found.append((i, e))
    for s, e in sorted(found, reverse=True):
        t = t[:s] + "<span class=hl>" + t[s:e] + "</span>" + t[e:]
    return t


def _md_table(t):
    # 마크다운 표(헤더행+구분행+본문)를 <table>로 변환. 이스케이프 이후 호출.
    if "|" not in t:
        return t
    is_row = lambda s: re.match(r"\s*\|.*\|\s*$", s)
    is_sep = lambda s: "|" in s and re.match(r"\s*\|?[\s:|-]*-{2,}[\s:|-]*\|?\s*$", s)
    cells = lambda s: [c.strip() for c in s.strip().strip("|").split("|")]
    lines = t.split("\n"); out = []; i = 0; n = len(lines)
    while i < n:
        if is_row(lines[i]) and i + 1 < n and is_sep(lines[i + 1]):
            head = cells(lines[i]); i += 2; body = []
            while i < n and is_row(lines[i]):
                body.append(cells(lines[i])); i += 1
            tb = ["<table><tr>" + "".join("<th>%s</th>" % c for c in head) + "</tr>"]
            for r in body:
                tb.append("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>")
            tb.append("</table>")
            out.append("".join(tb))
        else:
            out.append(lines[i]); i += 1
    return "\n".join(out)


def _base(t):
    # 텍스트 정규화: 난이도 메타라인 제거 → 不보정 → 한자→한글 → HTML 이스케이프 (cloze 번호부여 전)
    t = _RE_NAN.sub("", t)                    # 난이도 메타(인라인·괄호·콜론 등) 제거 → 태그로만
    t = _bu_bul(t)
    t = h2k(t, "substitution")
    return html.escape(t, quote=False)


def _fmt(t, hl=False, kws=None):
    # 서식(이스케이프 이후): 표→HTML / **볼드**→<b> / (답면) 노랑형광 / 색상 강조 / 공백 뒤 열거마커 앞 <br>
    t = _md_table(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    if hl:
        t = _highlight(t, kws=kws)
    t = _RE_CASE.sub(r"<span class=cn>\1</span>", t)
    t = _RE_LAW.sub(r"<span class=law>\1</span>", t)
    t = _RE_VERD.sub(r"<span class=vd>\1</span>", t)
    t = _RE_ENUM.sub(r"<br><span class=en>\1</span>", t)
    return re.sub(r"^(?:<br>)+", "", t.strip())


def conv(t, hl=False):
    if not t:
        return ""
    base = _base(t)
    # 답면 형광 시 per-card 캐시 조회(키=md5(_base(답면)), 인벤토리와 동일)
    kws = _HLCACHE.get(hashlib.md5(base.encode("utf-8")).hexdigest()) if (hl and _HLCACHE) else None
    return _fmt(base, hl, kws)


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
    if fn.startswith("사례풀이순서_"):   # #51 사례 풀이순서 카드 → 회독그룹 '사례'
        m = re.search(r"사례풀이순서_(.+?)_v37", fn)
        return "사례", (m.group(1) if m else "기타")
    if fn.startswith("포섭트리거_"):     # #51(E) 포섭사전 파생 카드 → 회독그룹 '포섭'
        m = re.search(r"포섭트리거_(.+?)_v37", fn)
        return "포섭", (m.group(1) if m else "기타")
    if fn.startswith("약점포섭_"):       # #52-B 채점 누락 파생 약점 카드 → 회독그룹 '약점'(증분 덱)
        m = re.search(r"약점포섭_(.+?)_v37", fn)
        return "약점", (m.group(1) if m else "기타")
    for p, g, s in BOOK:
        if fn.startswith(p):
            return g, s
    return None, None


_LABELS = r"(?:앞면|뒷면|빈칸|앞|뒤|Text|태그|난이도|출처)"

_FW_CLOZE = re.compile(r"【\s*(.+?)\s*】")
def _fw_cloze(s):
    # 방어: 전각괄호 클로즈 【x】 → {{x}} (v3.7는 {{}}만 허용; 레거시·드리프트 안전망)
    return _FW_CLOZE.sub(lambda m: "{{" + m.group(1).strip() + "}}", s) if s else s


def field(block, keys):
    # 라벨 변형 흡수: 앞|앞면, 뒤|뒷면. **라벨** / 라벨: / **라벨**\n내용 (콜론선택, 내용 다음줄 허용)
    # 경계: 다음 라벨 또는 가로줄(--- 카드 구분, 표 구분행 |---|는 제외) 또는 끝.
    alt = "|".join(keys)
    pat = (rf"\*{{0,2}}\s*(?:{alt})\s*\*{{0,2}}\s*[:：]?\s*"
           rf"(.*?)(?=\n\s*\*{{0,2}}\s*{_LABELS}\s*\*{{0,2}}\s*[:：]?|\n\s*-{{3,}}\s*(?:\n|$)|\Z)")
    m = re.search(pat, block, re.S)
    return m.group(1).strip(" *\n\t") if m else ""


def blocks_of(txt):
    """### 또는 **카드 단위로 분할 → (속성, 주제, 본문). 속성·주제는 블록헤더 우선, 없으면 직전 ## 헤더."""
    out = []
    cur = None
    h2attr = ""
    h2topic = ""
    for ln in txt.split("\n"):
        is_h = re.match(r"^#{2,6}\s", ln)
        if is_h or re.match(r"^\s*\*{0,2}\s*카드\s*[\dA-Za-z]", ln):
            if cur:
                out.append(cur)
            a = attr_of(ln)
            if ln.startswith("## ") and not ln.startswith("###"):
                h2attr = a            # h2 헤더는 컨텍스트(하위 **카드** attr)도 갱신
                mt = re.search(r"\[주제\]\s*([^/()\n]+)", ln)
                if mt:
                    h2topic = mt.group(1).strip().replace(" ", "")  # 주제 정규화(띄어쓰기 제거)
            cur = [a or h2attr, h2topic, ln + "\n"]
        elif cur:
            cur[2] += ln + "\n"
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
    seen = set()          # 내용 dedup(dkey, 총장수 보존) — guid와 분리(§8.1)
    cnt = defaultdict(lambda: [0, 0])  # deckname -> [basic, cloze]
    skipped = defaultdict(int)
    n_basic = n_cloze = 0
    hanja_cards = unnum_cloze = 0  # 검증: 한자 잔존·번호없는 cloze (둘 다 0이어야 정상)

    def get_deck(name):
        if name not in decks:
            decks[name] = genanki.Deck(did(name), name)
        return decks[name]

    # 고반복 프리스캔(2026-07-04): 같은 카드 내용이 서로 다른 책(bookkey) 2곳+에 등장 → '고반복' 태그
    def _ckey(blk):
        body = re.sub(r"(?m)^\s*(태그|난이도|출처)[ 	]*[:：].*$", "", blk)
        return re.sub(r"\s+", "", body)[:400]
    _freq = {}
    for fn in sorted(files):
        if fn in ("H", "H:") or not fn.endswith(".md") or "_TEMP" in fn:
            continue
        txt0 = open(os.path.join(SRC, fn), encoding="utf-8").read()
        if txt0.count("\n") < 30 or deck_of(fn)[0] is None:
            continue
        bk0 = re.split(r"_p\d|_llamaparse", fn)[0]
        for _a, _t, blk0 in blocks_of(txt0):
            k = _ckey(blk0)
            if len(k) >= 60:
                _freq.setdefault(k, set()).add(bk0)
        for cn0 in set(_RE_CASE.findall(txt0)):
            _freq.setdefault("CASE::" + cn0, set()).add(bk0)
    HIGHFREQ = {k for k, v in _freq.items() if len(v) >= 2}
    HIGHCASE = {k[6:] for k in HIGHFREQ if k.startswith("CASE::")}

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
        head_verify = re.findall(r"검증필요::\S+", txt[:400])  # 파일머리 태그(찌라시 law-mcp 등)

        for attr, topic, blk in blocks_of(txt):
            ap, dwi, bk, tx = field(blk, ["앞", "앞면"]), field(blk, ["뒤", "뒷면"]), field(blk, ["빈칸"]), field(blk, ["Text"])
            ap, dwi, bk, tx = _fw_cloze(ap), _fw_cloze(dwi), _fw_cloze(bk), _fw_cloze(tx)  # 방어: 【x】→{{x}}
            cloze_src = next((x for x in (bk, tx, dwi, ap) if x and "{{" in x), "")  # 앞(cloze): 흡수
            if not cloze_src and "{{" in blk and not (ap and "{{" in ap):
                body = blk.split("\n", 1)[1] if "\n" in blk else ""
                cloze_src = re.sub(r"(?m)^\s*\*{0,2}\s*카드\s*[\w-]*\s*\*{0,2}\s*", "", body).strip()
            nan = _RE_NAN.search(blk)
            tags = [f"과목::{subj}", f"속성::{attr or '기타'}", f"출처::{src}", f"회독그룹::{grp}"]
            if nan:
                tags.append(f"난이도::{nan.group(1).upper()}")  # 명시값만(미표기 카드는 무부착)
            if topic:
                tags.append(f"주제::{topic}")                    # ## [주제] 헤더(있는 파일만)
            for typ, num in re.findall(r"\[(변|모|입|행시|사시|법전)\s*(\d{2,4})\]", blk):
                tags.append(f"기출::{typ}{num}")                 # 본문 [변17]·[모25] 마커(원형 보존)
            tags += head_verify                                  # 파일머리 검증필요::
            m_tl = re.search(r"(?m)^[ \t]*태그[ \t]*[:：][ \t]*(.+)$", blk)  # 카드 '태그:' 줄에서 빌더 미도출 축만 흡수
            if m_tl:  # 과목/속성/출처/회독그룹은 빌더가 파일명·헤더서 도출 → 중복·충돌 방지 위해 제외
                _OK = ("단계", "증명책임", "주제", "난이도", "기출", "검증필요")
                tags += [kv for kv in re.findall(r"\S+?::\S+", m_tl.group(1)) if kv.split("::", 1)[0] in _OK]
            if _ckey(blk) in HIGHFREQ or any(cn in HIGHCASE for cn in set(_RE_CASE.findall(blk))):
                tags.append("고반복")                               # 같은 내용 또는 같은 판례가 2권+ 책 출현 = 고빈출 신호(강조)
            tags = list(dict.fromkeys(tags))                     # 중복 제거(순서 보존)
            made = False
            if cloze_src:
                ctext = _fmt(trim_blank(number_cloze(_base(cloze_src))))  # 서식은 cloze 번호부여·트림 뒤
                if "{{c" in ctext and not re.search(r"\{\{(?!c\d+::)", ctext):
                    g = genanki.guid_for(guid_seed(stem, "cloze", seq, explicit_uid=extract_uid(blk)))
                    seq += 1
                    dkey = ("C", src, re.sub(r"\s+", "", ctext))  # 내용 dedup은 guid와 분리(§8.1)
                    extra = "" if (cloze_src == ap or (ap and "{{" in ap)) else conv(ap)
                    nt = genanki.Note(model=CLOZE, fields=[ctext, extra, src], guid=g, tags=tags)
                    if dkey not in seen:
                        seen.add(dkey); get_deck(deckname).add_note(nt)
                        subj_decks[subj].add(deckname); cnt[deckname][1] += 1; n_cloze += 1
                        if CJK.search(ctext) or CJK.search(extra):
                            hanja_cards += 1
                        if re.search(r"\{\{(?!c\d+::)", ctext):
                            unnum_cloze += 1
                    made = True
            # Basic: 앞+뒤 / [OX-N] 선지=헤더+뒤만 / double(빈칸 cloze+완성문)
            head_front = re.sub(r"^\*+\s*카드\s*[\w-]*\s*\*+\s*", "",
                                re.sub(r"^#+\s*\[[^\]]*\]\s*", "", blk.split("\n", 1)[0])).strip()
            want_basic = (not cloze_src and dwi and (ap or head_front)) or (DOUBLE and cloze_src == bk and bk and dwi and "{{" not in dwi)
            if want_basic:
                front = conv(ap) or conv(head_front) or attr
                back = conv(dwi, hl=True)   # 답면만 노랑형광
                if front and back:
                    g = genanki.guid_for(guid_seed(stem, "basic", seq, explicit_uid=extract_uid(blk)))
                    seq += 1
                    dkey = ("B", src, re.sub(r"\s+", "", front + back))  # 내용 dedup은 guid와 분리(§8.1)
                    nt = genanki.Note(model=BASIC, fields=[front, back, src], guid=g, tags=tags)
                    if dkey not in seen:
                        seen.add(dkey); get_deck(deckname).add_note(nt)
                        subj_decks[subj].add(deckname); cnt[deckname][0] += 1; n_basic += 1
                        if CJK.search(front) or CJK.search(back):
                            hanja_cards += 1
                    made = True
            # 폴백: 평문 풀이순서 카드(앞/뒤/cloze 無, 제목+번호단계) → Basic(앞=제목 질문, 뒤=단계)
            if not made and "[풀이순서]" in blk.split("\n", 1)[0]:
                body = blk.split("\n", 1)[1] if "\n" in blk else ""
                body = re.sub(r"(?m)^\s*\*{0,2}\s*(?:단계|증명책임|태그)[ \t]*[:：].*$", "", body)
                body = trim_blank(body).strip()
                front = conv(head_front).strip()
                if front and body:
                    for kv in re.findall(r"(?:단계|증명책임|주제)::[^\s*]+", blk):
                        tags.append(kv)
                    tags = list(dict.fromkeys(tags))
                    fq = front + " — 풀이 순서?"
                    bk2 = conv(body, hl=True)
                    g = genanki.guid_for(guid_seed(stem, "basic", seq, explicit_uid=None))
                    seq += 1
                    dkey = ("B", src, re.sub(r"\s+", "", fq + bk2))
                    nt = genanki.Note(model=BASIC, fields=[fq, bk2, src], guid=g, tags=tags)
                    if dkey not in seen:
                        seen.add(dkey); get_deck(deckname).add_note(nt)
                        subj_decks[subj].add(deckname); cnt[deckname][0] += 1; n_basic += 1
                        if CJK.search(fq) or CJK.search(bk2):
                            hanja_cards += 1
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
    from datetime import datetime as _dt
    rep = ["# v37 apkg 빌드 리포트", f"- 정본 스냅샷: v37-{_dt.now():%Y-%m-%d} — 이후 신규 카드는 약점포섭_*(증분 덱 '약점')만 추가, 기존 카드파일 내용 수정 금지(안키 GUID 보존)",
           f"- Basic {n_basic} / Cloze {n_cloze} / 합 {n_basic + n_cloze}",
           f"- apkg {n_files}개 (과목×책종류 분할): {len(subj_decks)}과목 × 책종류별 → outputs/anki/v37/apkg/{{과목}}/{{회독그룹}}_v37.apkg", "",
           "| 덱 | Basic | Cloze |", "|---|---:|---:|"]
    for d in sorted(cnt):
        rep.append(f"| {d} | {cnt[d][0]} | {cnt[d][1]} |")
    rep.append("")
    rep.append(f"- 한자 잔존 카드: {hanja_cards}")
    rep.append(f"- 번호없는 cloze 카드: {unnum_cloze}")
    rep.append("- guid: 안정 note_key({파일stem}::{basic|cloze}::{헤더}::{occ}) 파생 (내용 수정해도 유지·헤더 앵커)")
    rep.append(f"- 서식: 표→<table> · 색상강조(cn 사건번호/law 조문/vd 결론/en 열거) · 답면 노랑형광(per-card LLM {len(_HLCACHE)}장 + 어휘 {len(_HLVOCAB)}종 폴백) · 열거마커 <br> · 난이도:: 태그(명시 카드) · 不 활음조보정")
    rep.append("- skip: " + ", ".join(f"{k}={v}" for k, v in skipped.items()))
    open(f"{OUT}/_apkg_report.md", "w", encoding="utf-8").write("\n".join(rep))
    print("\n".join(rep[:6]))
    print("skip:", dict(skipped))


if __name__ == "__main__":
    main()
