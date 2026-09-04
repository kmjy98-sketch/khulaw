# -*- coding: utf-8 -*-
"""검증 2단계: 제40조 정확 추출 + 네이버 판례 상세(법적성격) + 동영상/카카오 추가 탐색."""
import os
import sys
import io
import requests
import xml.etree.ElementTree as ET

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SKILL_DIR = r"H:\내 드라이브\.agent\skills\korean-law-mcp"
BASE = "https://www.law.go.kr/DRF"

OC = ""
with open(os.path.join(SKILL_DIR, ".env"), "r", encoding="utf-8") as f:
    for line in f:
        if line.strip().startswith("LAW_API_KEY="):
            OC = line.split("=", 1)[1].strip()


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


# 1) 제40조 모든 조문단위 출력
print("=== 제40조 단위 전체 (law_id=001591) ===")
root = get(f"{BASE}/lawService.do", {"target": "law", "ID": "001591"})
for unit in root.findall(".//조문단위"):
    if unit.findtext("조문번호", "") == "40":
        yn = unit.findtext("조문여부", "")
        ga = unit.findtext("조문가지번호", "")
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
        body = "\n".join(pieces)
        print(f"\n[조문여부={yn} 가지={ga} 제목={title}] 길이={len(body)}")
        if yn == "조문" or len(body) > 50:
            print(body[:4000])
print()

# 2) 네이버 판례 상세 (seq 612863)
print("=== 네이버 2023두32709 상세 (seq 612863) ===")
root = get(f"{BASE}/lawService.do", {"target": "prec", "ID": "612863"})
for tag in ["사건명", "사건번호", "선고일자", "법원명", "사건종류명"]:
    print(f"  {tag}:", norm(root.findtext(f'.//{tag}', '')))
print("  --- 판시사항 ---")
print(norm(root.findtext('.//판시사항', ''))[:1500])
print("  --- 판결요지(앞부분) ---")
print(norm(root.findtext('.//판결요지', ''))[:1200])
print("  --- 참조조문 ---")
print(norm(root.findtext('.//참조조문', ''))[:800])
print()

# 3) 동영상 건 / 카카오 추가 탐색
def search_prec(query, n=10):
    root = get(f"{BASE}/lawSearch.do", {"target": "prec", "query": query, "display": n})
    total = root.findtext(".//totalCnt", "0")
    out = []
    for p in root.findall(".//prec"):
        out.append((p.findtext("사건번호", ""), p.findtext("법원명", ""),
                    p.findtext("선고일자", ""), p.findtext("사건명", "")[:50]))
    return total, out


print("=== 추가 판례 탐색 ===")
for q in ["2023두38219", "동영상 검색", "카카오모빌리티 시장지배적", "가맹택시", "콜 차단"]:
    total, ps = search_prec(q)
    print(f"[query={q}] total={total}")
    for p in ps[:6]:
        print(f"  - {p[0]} | {p[1]} {p[2]} | {p[3]}")
    print()

print("=== DONE ===")
