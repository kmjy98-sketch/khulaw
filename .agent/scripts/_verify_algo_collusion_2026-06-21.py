# -*- coding: utf-8 -*-
"""알고리즘 담합 발제문 검증: 공정거래법 제40조 + 네이버/카카오 판례.
국가법령정보센터 DRF API 직접 호출 (cachetools 등 의존성 없음). 일회성(#42). 2026-06-21.
"""
import os
import sys
import io
import requests
import xml.etree.ElementTree as ET

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = r"H:\내 드라이브\.agent\skills\korean-law-mcp"
BASE = "https://www.law.go.kr/DRF"

# .env 에서 LAW_API_KEY 로드
OC = ""
env_path = os.path.join(SKILL_DIR, ".env")
with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("LAW_API_KEY=") and "=" in line:
            OC = line.split("=", 1)[1].strip()
print("OC key set:", bool(OC), "| len:", len(OC))
print()


def get(url, params):
    p = {"OC": OC, "type": "XML"}
    p.update(params)
    r = requests.get(url, params=p, timeout=40)
    r.raise_for_status()
    return ET.fromstring(r.text)


def norm(t):
    if not t:
        return ""
    return "\n".join(" ".join(ln.replace("\t", " ").split()) for ln in t.splitlines() if ln.strip())


# 1) 공정거래법 검색
print("=== 1. 공정거래법 검색 ===")
root = get(f"{BASE}/lawSearch.do", {"target": "law", "query": "독점규제 및 공정거래에 관한 법률", "display": 20})
law_id = None
for law in root.findall(".//law"):
    name = law.findtext("법령명한글", "")
    lid = law.findtext("법령ID", "")
    enf = law.findtext("시행일자", "")
    pub = law.findtext("공포번호", "")
    div = law.findtext("법령구분명", "")
    if name.strip() == "독점규제 및 공정거래에 관한 법률" and law_id is None:
        law_id = lid
    print(f"  {name} | ID:{lid} | 구분:{div} | 시행:{enf} | 공포번호:{pub}")
print("선택 law_id:", law_id)
print()

# 2) 제40조 전문
print("=== 2. 제40조 조문 전문 ===")
if law_id:
    root = get(f"{BASE}/lawService.do", {"target": "law", "ID": law_id})
    print("법령명:", root.findtext('.//법령명한글', ''), "| 시행:", root.findtext('.//시행일자', ''))
    for unit in root.findall(".//조문단위"):
        if unit.findtext("조문번호", "") == "40":
            title = norm(unit.findtext("조문제목", ""))
            pieces = []
            head = norm(unit.findtext("조문내용", ""))
            if head:
                pieces.append(head)
            for el in unit.iter():
                if el.tag in ("항내용", "호내용", "목내용"):
                    txt = norm(el.text or "")
                    if txt:
                        pieces.append(txt)
            print("--- 제40조:", title, "---")
            print("\n".join(pieces))
            break
print()

# 3) 판례 검색 helper
def search_prec(query, court=None, n=10):
    params = {"target": "prec", "query": query, "display": n}
    if court:
        params["curt"] = court
    root = get(f"{BASE}/lawSearch.do", params)
    total = root.findtext(".//totalCnt", "0")
    out = []
    for p in root.findall(".//prec"):
        out.append({
            "사건번호": p.findtext("사건번호", ""),
            "법원명": p.findtext("법원명", ""),
            "선고일자": p.findtext("선고일자", ""),
            "사건명": p.findtext("사건명", ""),
            "판례일련번호": p.findtext("판례일련번호", ""),
        })
    return total, out


print("=== 3. 네이버/검색알고리즘 판례 ===")
for q in ["네이버", "검색알고리즘", "시장지배적지위 남용 검색"]:
    total, ps = search_prec(q)
    print(f"[query={q}] total={total}")
    for p in ps[:10]:
        print(f"  - {p['사건번호']} | {p['법원명']} {p['선고일자']} | {p['사건명'][:45]} | seq:{p['판례일련번호']}")
    print()

print("=== 4. 카카오모빌리티 판례 ===")
for q in ["카카오모빌리티", "카카오 배차"]:
    total, ps = search_prec(q)
    print(f"[query={q}] total={total}")
    for p in ps[:10]:
        print(f"  - {p['사건번호']} | {p['법원명']} {p['선고일자']} | {p['사건명'][:45]} | seq:{p['판례일련번호']}")
    print()

print("=== DONE ===")
