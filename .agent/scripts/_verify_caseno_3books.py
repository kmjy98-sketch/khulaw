# -*- coding: utf-8 -*-
"""
3책(쟁점노트_소송집행·가족법·기초법리집행법) 카드의 사건번호 DRF 검증.
- 국가법령정보센터 판례검색 API(target=prec)로 distinct 사건번호 존재확인.
- 연도 정규화: 19XX → XX(2자리, 2000년 이전 DB 표기). 1차 실패 시 원형도 시도.
- found 사건번호의 API 선고일자 vs 카드 인접 선고일 대조 → 불일치(번호 맞고 날짜 OCR오류 후보) 추출.
- 캐시(.agent/state/caseno_verify_3books.json) 재개 가능. 비파괴(읽기·리포트만).
출력: 리포트 .agent/state/caseno_verify_3books_report.md
"""
import os, re, sys, json, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CARDS = "H:/내 드라이브/outputs/02_cards"
GLOBS = ["쟁점노트_소송집행_", "쟁점노트_가족법_", "기초법리집행법_"]
ENV = r"H:\내 드라이브\.agent\skills\korean-law-mcp\.env"
CACHE = "H:/내 드라이브/.agent/state/caseno_verify_3books.json"
REPORT = "H:/내 드라이브/.agent/state/caseno_verify_3books_report.md"

KEY = next(l.split("=", 1)[1].strip() for l in open(ENV, encoding="utf-8")
           if l.strip().startswith("LAW_API_KEY="))

CASE_CODE = (r"헌가|헌마|헌바|헌라|헌나|헌사|헌아|민상|형상|고합|고단|고정|가합|가단|다카|"
             r"다|도|두|마|머|모|므|르|즈|후|허|노|오|초|보|감|구|누|부|추|그|나|라|카")
RE_CASE = re.compile(r"(\d{2,4}(?:" + CASE_CODE + r")\d{1,6})")
# 선고일 + (쉼표) + 사건번호 인접 (대판 2009.5.14, 2009다100096)
RE_DATEPAIR = re.compile(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?\s*[,，]?\s*"
                         r"(\d{2,4}(?:" + CASE_CODE + r")\d{1,6})")


def norm(cn):
    """19XX → XX (2000년 이전 DB 2자리 표기)."""
    m = re.match(r"^19(\d{2})(.+)$", cn)
    return m.group(1) + m.group(2) if m else cn


def files():
    return [os.path.join(CARDS, f) for f in os.listdir(CARDS)
            if f.endswith("_cards.md") and any(f.startswith(g) for g in GLOBS)]


def collect():
    """distinct 사건번호 + (사건번호 -> 카드인접 선고일 set)."""
    cases = set()
    card_dates = {}  # caseno -> set of (Y,M,D)
    for path in files():
        txt = open(path, encoding="utf-8").read()
        for cn in RE_CASE.findall(txt):
            cases.add(cn)
        for y, m, d, cn in RE_DATEPAIR.findall(txt):
            card_dates.setdefault(cn, set()).add((int(y), int(m), int(d)))
    return cases, card_dates


def api_search(q):
    params = {"OC": KEY, "target": "prec", "type": "XML", "query": q, "display": 50, "page": 1}
    url = "https://www.law.go.kr/DRF/lawSearch.do?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                root = ET.fromstring(r.read().decode("utf-8", "replace"))
            out = []
            for p in root.findall(".//prec"):
                out.append((p.findtext("사건번호", "").replace(" ", ""),
                            p.findtext("선고일자", ""), p.findtext("법원명", ""),
                            p.findtext("사건명", "")))
            return out
        except Exception as e:
            if attempt == 2:
                return {"_err": str(e)}
            time.sleep(1 + attempt)


def verify_one(cn):
    """정규화형 우선, 실패 시 원형. 반환: dict(found, queried, 선고일자, 법원명, 사건명)."""
    for q in dict.fromkeys([norm(cn), cn]):  # 중복 제거, 순서 보존
        hits = api_search(q)
        if isinstance(hits, dict):  # error
            return {"found": None, "err": hits["_err"], "queried": q}
        exact = [h for h in hits if h[0] == q]
        if exact:
            h = exact[0]
            return {"found": True, "queried": q, "sgil": h[1], "court": h[2], "name": h[3]}
        time.sleep(0.12)
    return {"found": False, "queried": norm(cn)}


def main():
    cases, card_dates = collect()
    cases = sorted(cases)
    print(f"distinct 사건번호: {len(cases)}")
    print(f"카드 인접 선고일 보유: {len(card_dates)}")

    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE, encoding="utf-8"))
        print(f"캐시 로드: {len(cache)}건 (재개)")

    t0 = time.time()
    for i, cn in enumerate(cases, 1):
        if cn in cache and cache[cn].get("found") is not None:
            continue  # 성공/명확실패만 스킵, 에러는 재시도
        cache[cn] = verify_one(cn)
        time.sleep(0.12)
        if i % 50 == 0:
            json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
            el = time.time() - t0
            print(f"  {i}/{len(cases)}  ({el:.0f}s)")
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)

    # 집계
    found = [c for c in cases if cache[c].get("found") is True]
    notfound = [c for c in cases if cache[c].get("found") is False]
    errs = [c for c in cases if cache[c].get("found") is None]

    # 선고일 불일치 (found + 카드인접일자 존재 + API일자와 불일치)
    def apidate(c):
        s = cache[c].get("sgil", "")  # "2000.05.16"
        m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", s)
        return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    mismatch = []
    for c in found:
        if c in card_dates:
            ad = apidate(c)
            if ad and ad not in card_dates[c]:
                mismatch.append((c, sorted(card_dates[c]), ad, cache[c].get("court", "")))

    rep = ["# 3책 사건번호 DRF 검증 리포트", "",
           f"- distinct 사건번호: **{len(cases)}**",
           f"- DB 정확매치(found): **{len(found)}** ({len(found)*100//max(len(cases),1)}%)",
           f"- 미수록(not-found): **{len(notfound)}** — OCR오류 후보 + 공개DB 미수록 혼재(자동삭제 금지)",
           f"- API 에러(재시도 대상): **{len(errs)}**", "",
           f"## 선고일 불일치 (found인데 카드 인접 선고일≠API) — **{len(mismatch)}건** (고신뢰 수정후보)", ""]
    if mismatch:
        rep.append("| 사건번호 | 카드 선고일 | API 선고일 | 법원 |")
        rep.append("|---|---|---|---|")
        for c, cd, ad, court in mismatch:
            cds = "; ".join(f"{y}.{m}.{d}" for y, m, d in cd)
            rep.append(f"| {c} | {cds} | {ad[0]}.{ad[1]}.{ad[2]} | {court} |")
    else:
        rep.append("(없음)")
    rep += ["", f"## 미수록 사건번호 ({len(notfound)}건) — 검토용(OCR오류 의심만 수정)", ""]
    rep.append("```")
    rep += notfound
    rep.append("```")
    if errs:
        rep += ["", f"## API 에러 {len(errs)}건 (재실행 시 자동 재시도)", "```"] + errs + ["```"]
    open(REPORT, "w", encoding="utf-8").write("\n".join(rep))
    print(f"\nfound {len(found)} / notfound {len(notfound)} / err {len(errs)} / 선고일불일치 {len(mismatch)}")
    print("리포트:", REPORT)


if __name__ == "__main__":
    main()
