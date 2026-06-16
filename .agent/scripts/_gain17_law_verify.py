# 일회성: 가인17 민사예선 참고서면용 조문·판례 검증 (국가법령정보센터 Open API 직접 호출)
import json, os, sys, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")

ENV = r"H:\내 드라이브\.agent\skills\korean-law-mcp\.env"
key = None
for line in open(ENV, encoding="utf-8"):
    if line.startswith("LAW_API_KEY"):
        key = line.split("=", 1)[1].strip()
if not key:
    sys.exit("API 키 없음")

BASE_S = "http://www.law.go.kr/DRF/lawSearch.do"
BASE_V = "http://www.law.go.kr/DRF/lawService.do"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def jo(law_mst, jo_no, label):
    # 조문 단위 조회: JO=6자리(조 4 + 항 2)
    url = f"{BASE_V}?OC={key}&target=law&type=JSON&MST={law_mst}&JO={jo_no}"
    try:
        d = fetch(url)
        unit = d.get("법령", {}).get("조문", {}).get("조문단위", {})
        if isinstance(unit, list):
            unit = unit[0]
        content = unit.get("조문내용", "")
        items = unit.get("항", [])
        out = [content]
        if isinstance(items, dict):
            items = [items]
        for h in items or []:
            out.append(str(h.get("항내용", "")))
        print(f"\n===== {label} =====")
        print("\n".join(x for x in out if x))
    except Exception as e:
        print(f"\n===== {label} ===== 오류: {e}")

def find_mst(name):
    url = f"{BASE_S}?OC={key}&target=law&type=JSON&query={urllib.parse.quote(name)}"
    d = fetch(url)
    laws = d.get("LawSearch", {}).get("law", [])
    if isinstance(laws, dict):
        laws = [laws]
    for l in laws:
        if l.get("법령명한글", "").strip() == name:
            return l.get("법령일련번호")
    return laws[0].get("법령일련번호") if laws else None

def prec_search(q, label, max_n=3):
    url = f"{BASE_S}?OC={key}&target=prec&type=JSON&query={urllib.parse.quote(q)}"
    try:
        d = fetch(url)
        ps = d.get("PrecSearch", {}).get("prec", [])
        if isinstance(ps, dict):
            ps = [ps]
        print(f"\n##### 판례검색 [{label}] q='{q}' — {len(ps)}건")
        for p in ps[:max_n]:
            print(f"- {p.get('사건번호')} | {p.get('선고일자')} | {p.get('법원명')} | {p.get('사건명')} | id={p.get('판례일련번호')}")
        return ps[:max_n]
    except Exception as e:
        print(f"\n##### 판례검색 [{label}] 오류: {e}")
        return []

def prec_detail(pid, label):
    url = f"{BASE_V}?OC={key}&target=prec&type=JSON&ID={pid}"
    try:
        d = fetch(url)
        b = d.get("PrecService", d.get("판례", {}))
        print(f"\n***** 판례본문 [{label}] {b.get('사건번호','')} {b.get('선고일자','')}")
        for k in ("판시사항", "판결요지"):
            v = (b.get(k) or "").replace("<br/>", "\n").replace("&nbsp;", " ")
            if v:
                print(f"[{k}]\n{v[:2200]}")
    except Exception as e:
        print(f"\n***** 판례본문 [{label}] 오류: {e}")

# ---- 조문 ----
mst_민법 = find_mst("민법")
mst_가담 = find_mst("가등기담보 등에 관한 법률")
print(f"민법 MST={mst_민법}, 가담법 MST={mst_가담}")
for jo_no, label in [("036600", "민법 제366조"), ("019700", "민법 제197조"), ("020100", "민법 제201조"), ("074100", "민법 제741조")]:
    jo(mst_민법, jo_no, label)
for jo_no, label in [("001000", "가담법 제10조"), ("001200", "가담법 제12조"), ("001300", "가담법 제13조")]:
    jo(mst_가담, jo_no, label)

# ---- 판례: 사건번호 직접 ----
targets = [
    ("2010다52140", "관습법지 기준시점-압류·가압류"),
    ("2009다62059", "저당권설정 당시 기준"),
    ("2003다26051", "나대지 저당 법지부정"),
    ("96다31895", "합의해제 가등기유용"),
    ("92다7221", "건축중 건물 법지"),
]
for no, label in targets:
    ps = prec_search(no, label, max_n=2)
    for p in ps:
        if p.get("사건번호", "").endswith(no):
            prec_detail(p.get("판례일련번호"), label)
            break

# ---- 판례: 키워드 ----
for q, label in [
    ("미등기건물 양수인 철거", "미등기 양수인 철거의무"),
    ("독립된 건물 기둥 지붕 주벽", "독립건물 요건"),
    ("선의의 점유자 과실취득 부당이득", "선의점유 과실수취"),
    ("담보가등기 여부 거래의 실질", "담보가등기 판단기준"),
]:
    ps = prec_search(q, label, max_n=3)
    if ps:
        prec_detail(ps[0].get("판례일련번호"), label)
