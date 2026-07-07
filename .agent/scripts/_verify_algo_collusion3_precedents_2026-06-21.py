# -*- coding: utf-8 -*-
"""쟁점 보강: 정보교환·의식적병행행위·합의추정 핵심 판례 탐색 (국가법령정보 API)."""
import os, sys, io, requests
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
    p = {"OC": OC, "type": "XML"}; p.update(params)
    r = requests.get(url, params=p, timeout=40); r.raise_for_status()
    return ET.fromstring(r.text)

def norm(t):
    if not t: return ""
    return "\n".join(" ".join(ln.replace("\t"," ").split()) for ln in t.splitlines() if ln.strip())

def search(query, n=10):
    root = get(f"{BASE}/lawSearch.do", {"target":"prec","query":query,"display":n})
    total = root.findtext(".//totalCnt","0")
    out=[]
    for p in root.findall(".//prec"):
        out.append((p.findtext("사건번호",""),p.findtext("법원명",""),
                    p.findtext("선고일자",""),p.findtext("사건명","")[:55],
                    p.findtext("판례일련번호","")))
    return total,out

for q in ["부당한 공동행위 합의 추정 정보교환","라면 가격 담합","의식적 병행행위",
          "정보교환 합의","비씨카드 공동행위","과점시장 가격 동조","합의 추정 복멸"]:
    total,ps = search(q)
    print(f"=== [{q}] total={total} ===")
    for p in ps[:8]:
        print(f"  - {p[0]} | {p[1]} {p[2]} | {p[3]} | seq:{p[4]}")
    print()
print("DONE")
