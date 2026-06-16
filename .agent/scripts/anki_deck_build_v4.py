# -*- coding: utf-8 -*-
"""
anki_deck_build_v4.py — outputs/02_cards/*.md → v4 덱별 Anki TSV 빌드
- 덱 구조 v4 (2026-06-10): 기본서 / 암기장-객관식 / 암기장-사례형 × 과목. 김준호(교수저)는 제외.
- v4.1 (2026-06-11): ①과목 전부 분할 — 덱 과목을 카드별 `과목::` 태그로 결정(민법·민사소송법·형법·헌법.
  과목::민사법은 전량 민법으로 정규화 — 쟁점노트 카드화분이 재산법뿐임을 확인). ②색상 키워드 강조 —
  사건번호(파랑)·조문(초록)·결론어(빨강)·열거마커/요건개수(주황)·O(초록)/X(빨강) 인라인 span.
- 요건 통짜 변환: 속성::요건 + 뒤(Back)에 ①②… 2개 이상 → overlapping cloze (마커는 빈칸 밖).
- 출력: outputs/anki/v4/{덱}_basic.tsv / _cloze.tsv (Anki 파일 헤더 #deck 포함) + _manifest_v4.md
"""
import hashlib
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

SRC = Path("H:/내 드라이브/outputs/02_cards")
OUT = Path("H:/내 드라이브/outputs/anki/v4")

# v4.1: 파일 prefix → 회독 그룹 (과목은 카드 태그에서 — preset 상속을 위해 그룹이 상위 덱)
GROUP_MAP = [
    ("논점민법재산법", "기본서"),
    ("김형총", "기본서"),
    ("헌법300", "암기장-객관식"),
    ("강성민1", "암기장-객관식"),
    ("강성민2", "암기장-객관식"),
    ("강성민3", "암기장-객관식"),
    ("유니온헌", "암기장-객관식"),
    ("쟁점노트", "암기장-객관식"),
    ("논민소", "암기장-객관식"),
    ("신민사", "암기장-객관식"),
    ("compact형총", "암기장-객관식"),
    ("반반형법", "암기장-객관식"),
    ("해커스헌", "암기장-사례형"),
    ("민사례1", "암기장-사례형"),
    ("사례민총", "암기장-사례형"),
    ("사례물권", "암기장-사례형"),
    ("사례채권", "암기장-사례형"),
    ("사례담보", "암기장-사례형"),
    ("사례가족", "암기장-사례형"),
    ("작은변사기", "암기장-사례형"),
]
# 파일 prefix → 태그 무과목 시 폴백 과목 (현재 27,376행 전부 과목:: 보유 — 형식상 안전망)
GROUP_FALLBACK_SUBJ = {
    "논점민법재산법": "민법", "김형총": "형법", "헌법300": "헌법", "강성민": "헌법",
    "유니온헌": "헌법", "쟁점노트": "민법", "논민소": "민사소송법", "신민사": "민법",
    "compact형총": "형법", "반반형법": "형법", "해커스헌": "헌법", "민사례1": "민법",
    "사례": "민법", "작은변사기": "형법",
}
SUBJ_NORM = {"민사법": "민법"}  # 쟁점노트 카드화분 = 재산법 전부 (소송·집행 미카드화, 2026-06-11 확인)
TAG_SUBJ = re.compile(r"과목::(\S+)")
SKIP_PREFIX = ("김준호",)  # 교수저 — 사용자 결정: 카드화·임포트 무시 (md 보존)
SKIP_FILES = {
    "논점민법재산법_p031-060_cards.md",  # easyocr 구판 — llamaparse 판과 p31-60 중복
    "_사례형비교_사례1.md",              # 방식 비교 문서 (카드 아님)
}

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮"
MAX_CLOZE = 5  # cloze_integrity: 한 카드 5개 초과 금지

# 줄바꿈: 공백+원문자 마커(열거) 앞에 <br> 삽입. "(§444①)"처럼 붙어 있는 항 참조는 비대상.
BR_MARK = re.compile(r" ([①-⑮㉠-㉭])")

# ── v4.1 색상 강조 (라이트/다크 모두 가독되는 톤) ──────────────────────────
C_CASE = "#2e86d1"  # 사건번호 — 파랑
C_LAW = "#1a9a55"   # 조문 — 초록
C_VERD = "#e5484d"  # 결론·판단어 — 빨강 볼드
C_MARK = "#d97706"  # 열거 마커·요건 개수 — 주황 볼드
RE_CASE = re.compile(r"\d{2,4}(?:헌[가나다라마바사]|다|도|두|므|스|마|누|허|후|그|카|바)\d{1,7}")
RE_LAW = re.compile(r"§\d+(?:의\d+)?[①-⑮]*|제\d+조(?:의\d+)?(?:\s?제\d+항|[①-⑮]+)?")
RE_VERD = re.compile(
    r"헌법불합치|한정위헌|한정합헌|위헌|합헌|무효|부적법|적법|위법|각하|기각|인용|"
    r"파기환송|파기자판|파기|유죄|무죄|불성립|추정|간주|의제"
)
RE_MARK = re.compile(r"(?<![0-9§①-⑮])[①-⑮㉠-㉭]")  # 숫자·§·체인 뒤 항 참조는 제외
RE_OX = re.compile(r"(?<![A-Za-z])([OX])(?![A-Za-z])")
RE_CNT = re.compile(r"\(\d+가지\)")


def _w(color: str, bold: bool):
    style = f"color:{color}" + (";font-weight:700" if bold else "")
    return lambda m: f'<span style="{style}">{m.group(0)}</span>'


def colorize(s: str) -> str:
    """키워드 인라인 색상 강조. 이스케이프·<br> 삽입 이후에 호출 (cloze {{cN::}} 구문 비침범)."""
    s = RE_CASE.sub(_w(C_CASE, False), s)
    s = RE_LAW.sub(_w(C_LAW, False), s)
    s = RE_VERD.sub(_w(C_VERD, True), s)
    s = RE_MARK.sub(_w(C_MARK, True), s)
    s = RE_CNT.sub(_w(C_MARK, True), s)
    s = RE_OX.sub(
        lambda m: '<span style="color:{};font-weight:700">{}</span>'.format(
            "#1a9a55" if m.group(1) == "O" else "#e5484d", m.group(1)
        ),
        s,
    )
    return s


# ── v4.2 키워드 형광 마킹: LLM 추출 캐시(.agent/state/anki_keyword_cache.jsonl) 적용 ──
KW_CACHE = Path("H:/내 드라이브/.agent/state/anki_keyword_cache.jsonl")
CZ_CACHE = Path("H:/내 드라이브/.agent/state/anki_cloze_kw_cache.jsonl")
HL_OPEN = '<span style="background:#ffe066;color:#332600;border-radius:3px;">'
MARKS = {}
CLOZE_MARKS = {}

RE_DEL = re.compile(r"\{\{c\d+::(.*?)\}\}")

# 키워드 품질 필터(v4.2): 추출기가 뱉은 조사-끝 파편 토큰("처분이"·"재산으로" 등)은 마킹·빈칸 대상에서 제외
_PARTICLES = set("이가을를은는의로에와과도며")
MAX_ADD_BLANKS = 4  # cloze 카드당 추가 가림 상한 (긴 구절 우선)


def good_kw(kw: str) -> bool:
    kw = kw.strip()
    if len(kw) < 2 or "{{" in kw or "}}" in kw:
        return False
    if len(kw) <= 4 and kw[-1] in _PARTICLES:
        return False
    return True


def cz_plain(text: str) -> str:
    """cloze Text에서 빈칸 구문을 벗긴 평문 (키워드 추출·캐시 키용)."""
    return RE_DEL.sub(r"\1", text)


def cz_key(text: str) -> str:
    return hashlib.md5(cz_plain(text).encode("utf-8")).hexdigest()


def augment_cloze(text: str, kws) -> str:
    """'빈칸 여러 개' 보강: 키워드를 기존 첫 빈칸과 같은 인덱스로 추가 가림(카드 수 불변, 문제지 스타일).
    기존 빈칸 영역과 겹치는 키워드는 건너뛴다."""
    m = re.search(r"\{\{c(\d+)::", text)
    idx = m.group(1) if m else "1"
    taken = [(s.start(), s.end()) for s in re.finditer(r"\{\{c\d+::.*?\}\}", text)]
    add = []
    for kw in sorted({k.strip() for k in kws}, key=len, reverse=True):
        if len(add) >= MAX_ADD_BLANKS:
            break
        if not good_kw(kw):
            continue
        start = 0
        while True:
            i = text.find(kw, start)
            if i < 0:
                break
            j = i + len(kw)
            if all(j <= s or i >= e for s, e in taken):
                taken.append((i, j))
                add.append((i, j))
                break
            start = i + 1
    for i, j in sorted(add, reverse=True):
        text = text[:i] + "{{c" + idx + "::" + text[i:j] + "}}" + text[j:]
    return text


def bk_key(back: str) -> str:
    return hashlib.md5(back.encode("utf-8")).hexdigest()


def load_marks():
    for path, store in ((KW_CACHE, MARKS), (CZ_CACHE, CLOZE_MARKS)):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
                if o.get("kw"):
                    store[o["k"]] = o["kw"]
            except json.JSONDecodeError:
                continue


def apply_marks(text: str, kws) -> str:
    """이스케이프된 본문에 키워드 형광 마킹 (긴 키워드 우선, 첫 등장 1회, 겹침 금지)."""
    taken = []
    for kw in sorted({k.strip() for k in kws}, key=len, reverse=True):
        if not good_kw(kw):
            continue
        k = kw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        start = 0
        while True:
            i = text.find(k, start)
            if i < 0:
                break
            j = i + len(k)
            if all(j <= s or i >= e for s, e in taken):
                taken.append((i, j))
                break
            start = i + 1
    for i, j in sorted(taken, reverse=True):
        text = text[:i] + HL_OPEN + text[i:j] + "</span>" + text[j:]
    return text


def fmt(field: str, marks=None) -> str:
    """Anki HTML 모드용 필드 포맷: 이스케이프 + 키워드 형광 + 열거 마커 앞 줄바꿈 + 색상 강조."""
    field = field.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if marks:
        field = apply_marks(field, marks)
    field = BR_MARK.sub(r"<br>\1", field)
    return colorize(field)


def group_for(fname: str):
    for p, g in GROUP_MAP:
        if fname.startswith(p):
            return g, p
    return None, None


def deck_of(group: str, prefix: str, tags: str) -> str:
    """그룹::과목 덱 결정 — 과목은 카드 태그(과목::) 우선, 없으면 prefix 폴백."""
    m = TAG_SUBJ.search(tags or "")
    if m:
        subj = SUBJ_NORM.get(m.group(1), m.group(1))
    else:
        subj = next(
            (s for p, s in GROUP_FALLBACK_SUBJ.items() if prefix.startswith(p) or p.startswith(prefix)),
            "기타",
        )
    return f"{group}::{subj}"


def parse_tsv_blocks(text: str):
    for m in re.finditer(r"```tsv\s*\n(.*?)```", text, re.S):
        lines = [l for l in m.group(1).split("\n") if l.strip()]
        if not lines:
            continue
        yield lines[0].rstrip(), [l.rstrip() for l in lines[1:] if "\t" in l]


def convert_yogeon(front: str, back: str, src: str, tags: str):
    """통짜 요건 Back → overlapping cloze Text 목록 (5개 초과 시 분할)."""
    marks_pat = "([" + CIRCLED + "])"
    parts = re.split(marks_pat, back)
    pre = parts[0].strip()
    pairs = []  # (마커, 본문)
    for i in range(1, len(parts) - 1, 2):
        seg = parts[i + 1].strip()
        if seg:
            pairs.append((parts[i], seg))
    if len(pairs) < 2:
        return None
    n = len(pairs)
    chunks = [pairs[i:i + MAX_CLOZE] for i in range(0, n, MAX_CLOZE)]
    texts = []
    for ci, chunk in enumerate(chunks):
        stem = f"{front} ({n}가지)" + (" (계속)" if ci else "")
        body = " ".join(
            f"{mark} {{{{c{j + 1}::{seg}}}}}" for j, (mark, seg) in enumerate(chunk)
        )
        lead = f" {pre}" if (pre and ci == 0) else ""
        texts.append(f"{stem}:{lead} {body}".replace("\t", " "))
    new_tags = tags.strip() + " 변환::요건클로즈"
    return [(t, src, new_tags) for t in texts]


def collect():
    """02_cards/*.md 파싱·변환 → (basic, cloze, meta). 빌드와 키워드 슬라이서가 공용."""
    basic = defaultdict(list)   # deck -> [(front, back, src, tags)]
    cloze = defaultdict(list)   # deck -> [(text, src, tags)]
    converted = split_cards = 0
    skipped, unknown = [], set()
    errors = defaultdict(int)  # (file, 사유) -> 행 수

    files = sorted(p for p in SRC.glob("*.md") if p.is_file())
    for f in files:
        if f.name in SKIP_FILES or f.name.startswith(SKIP_PREFIX):
            skipped.append(f.name)
            continue
        group, gprefix = group_for(f.name)
        if group is None:
            unknown.add(f.name)
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for header, rows in parse_tsv_blocks(text):
            first = header.split("\t")[0].strip()
            for r in rows:
                cols = r.split("\t")
                if first == "Text":
                    if len(cols) != 3:
                        errors[(f.name, f"cloze {len(cols)}열")] += 1
                        continue
                    tx, sc, tg = (c.strip() for c in cols)
                    if "{{c" not in tx:
                        errors[(f.name, "cloze 빈칸없음")] += 1
                        continue
                    deck = deck_of(group, gprefix, tg)
                    if group == "암기장-사례형":
                        # v4.2 분리: 사례집 포섭·판례 문장 cloze는 암기장(문장 암기 성질)으로.
                        # 사례형 덱에는 사례 구조 카드(논점추출 Basic)만 남긴다.
                        deck = deck.replace("암기장-사례형::", "암기장-객관식::", 1)
                        tg += " 분리::사례집포섭"
                    cloze[deck].append((tx, sc, tg))
                elif len(cols) == 7:
                    # v3.6 rule 스키마: 룰명|요건|효과|예외/단서|근거조문원문|출처|태그
                    rm, yg, hg, ye, jm, sc, tg = (
                        "" if c.strip() in ("—", "–", "-") else c.strip() for c in cols
                    )
                    deck = deck_of(group, gprefix, tg)
                    if yg and sum(yg.count(c) for c in CIRCLED) >= 2:
                        conv = convert_yogeon(rm, yg, sc, tg)
                        if conv:
                            converted += 1
                            split_cards += len(conv) - 1
                            cloze[deck].extend(conv)
                    elif yg:
                        basic[deck].append((f"{rm}?", yg, sc, tg))
                    if hg:
                        basic[deck].append((f"{rm} — 효과?", hg, sc, tg))
                    if ye:
                        basic[deck].append((f"{rm} — 예외/단서?", ye, sc, tg))
                    if jm:
                        basic[deck].append((f"{rm} — 근거조문 원문?", jm, sc, tg))
                elif len(cols) == 6 and "::" in cols[-1]:
                    # rule 7열에서 근거조문원문 누락 변형
                    rm, yg, hg, ye, sc, tg = (
                        "" if c.strip() in ("—", "–", "-") else c.strip() for c in cols
                    )
                    deck = deck_of(group, gprefix, tg)
                    if yg and sum(yg.count(c) for c in CIRCLED) >= 2:
                        conv = convert_yogeon(rm, yg, sc, tg)
                        if conv:
                            converted += 1
                            split_cards += len(conv) - 1
                            cloze[deck].extend(conv)
                    elif yg:
                        basic[deck].append((f"{rm}?", yg, sc, tg))
                    if hg:
                        basic[deck].append((f"{rm} — 효과?", hg, sc, tg))
                    if ye:
                        basic[deck].append((f"{rm} — 예외/단서?", ye, sc, tg))
                elif len(cols) == 4:  # 앞/뒤/출처/태그 (사실관계→판시 변형 포함)
                    fr, bk, sc, tg = (c.strip() for c in cols)
                    deck = deck_of(group, gprefix, tg)
                    if "속성::요건" in tg and sum(bk.count(c) for c in CIRCLED) >= 2:
                        conv = convert_yogeon(fr, bk, sc, tg)
                        if conv:
                            converted += 1
                            split_cards += len(conv) - 1
                            cloze[deck].extend(conv)
                            continue
                    basic[deck].append((fr, bk, sc, tg))
                elif len(cols) == 3 and "::" in cols[-1]:
                    # 앞/뒤/태그 변형 (출처 열 누락 — 태그의 출처:: 토큰에서 복원)
                    fr, bk, tg = (c.strip() for c in cols)
                    m = re.search(r"출처::(\S+)", tg)
                    sc = m.group(1) if m else ""
                    basic[deck_of(group, gprefix, tg)].append((fr, bk, sc, tg))
                else:
                    errors[(f.name, f"basic {len(cols)}열")] += 1

    return basic, cloze, {
        "converted": converted, "split_cards": split_cards,
        "skipped": skipped, "unknown": unknown, "errors": errors,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(parents=True, exist_ok=True)
    load_marks()
    basic, cloze, meta = collect()
    converted, split_cards = meta["converted"], meta["split_cards"]
    skipped, unknown, errors = meta["skipped"], meta["unknown"], meta["errors"]
    stats = defaultdict(lambda: [0, 0])  # deck -> [basic, cloze]
    marked_rows = augmented_rows = 0

    for deck in sorted(set(basic) | set(cloze)):
        safe = deck.replace("::", "_")
        if basic.get(deck):
            p = OUT / f"{safe}_basic.tsv"
            with p.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write("#separator:tab\n#html:true\n")
                fh.write(f"#deck:{deck}\n")
                fh.write("#columns:Front\tBack\t출처\tTags\n#tags column:4\n")
                for fr, bk, sc, tg in basic[deck]:
                    marks = MARKS.get(bk_key(bk))
                    if marks:
                        marked_rows += 1
                    fh.write("\t".join((fmt(fr), fmt(bk, marks), sc, tg)) + "\n")
            stats[deck][0] = len(basic[deck])
        if cloze.get(deck):
            p = OUT / f"{safe}_cloze.tsv"
            with p.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write("#separator:tab\n#html:true\n#notetype:Cloze\n")
                fh.write(f"#deck:{deck}\n")
                fh.write("#columns:Text\t출처\tTags\n#tags column:3\n")
                for tx, sc, tg in cloze[deck]:
                    kws = CLOZE_MARKS.get(cz_key(tx))
                    if kws:
                        tx2 = augment_cloze(tx, kws)
                        if tx2 != tx:
                            augmented_rows += 1
                            tx = tx2
                    fh.write("\t".join((fmt(tx), sc, tg)) + "\n")
            stats[deck][1] = len(cloze[deck])

    lines = ["# v4 덱 빌드 manifest (anki_deck_build_v4.py)", ""]
    lines.append("- v4.1 (2026-06-11): 덱 과목 전부 분할(카드 `과목::` 태그 기준, 민사법→민법 정규화) + 색상 키워드 강조(사건번호 파랑·조문 초록·결론어 빨강볼드·열거마커/요건개수 주황볼드·O초록/X빨강)")
    lines.append("")
    lines.append("| 덱 | Basic | Cloze | 합계 |")
    lines.append("|---|---:|---:|---:|")
    tb = tc = 0
    for deck in sorted(stats):
        b, c = stats[deck]
        tb += b; tc += c
        lines.append(f"| {deck} | {b} | {c} | {b + c} |")
    lines.append(f"| **합계** | **{tb}** | **{tc}** | **{tb + tc}** |")
    lines.append("")
    lines.append(f"- 요건 통짜→cloze 변환: {converted}장 (5개 초과 분할 +{split_cards}장, 태그 `변환::요건클로즈`)")
    lines.append(f"- 키워드 형광 마킹(Basic Back, v4.2): 캐시 {len(MARKS)}건 / 적용 행 {marked_rows}")
    lines.append(f"- cloze 빈칸 보강(같은 인덱스 추가 가림, v4.2): 캐시 {len(CLOZE_MARKS)}건 / 보강 행 {augmented_rows}")
    lines.append("- 사례형 분리(v4.2): 사례집 포섭·판례 cloze → 암기장-객관식::{과목} (태그 `분리::사례집포섭`). 사례형 덱은 사례 구조 Basic만")
    lines.append(f"- 제외 파일 {len(skipped)}개: 김준호*(교수저 무시), easyocr 구판, 비교문서")
    if unknown:
        lines.append(f"- 미매핑 파일 {len(unknown)}개: " + ", ".join(sorted(unknown)))
    if errors:
        total_err = sum(errors.values())
        lines.append(f"- 열 수 오류 {total_err}행 (스킵, 파일·사유별):")
        lines.extend(f"  - {fn} ({why}): {n}행" for (fn, why), n in sorted(errors.items()))
    (OUT / "_manifest_v4.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
