#!/usr/bin/env python
"""사건번호 샘플 검증 — cost_effective OCR이 사건번호를 위조했는지 점검 (#34), 2026-06-20

국가법령정보센터 DRF API(target=prec)로 OCR 추출 사건번호의 실존/일치를 대조.
- 전수(4,730 유니크) 대신 샘플(고빈도 + 무작위)로 OCR anchor 신뢰도 추정.
- 주의: DRF는 주로 '공개 대법원 판례' 수록 → not-found가 곧 위조는 아님(미수록 하급심 등).
  따라서 'found+정확일치'=확정 실존, 'not-found'=판단보류로 해석.

실행: <python.org python> .agent/scripts/_verify_caseno_sample_2026-06-20.py
"""
import os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
OCR = Path(r"H:\내 드라이브\outputs\01_ocr_llamaparse")
ENV = Path(r"H:\내 드라이브\.agent\skills\korean-law-mcp\.env")

# OC 키 로드
oc = ""
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("LAW_API_KEY="):
        oc = line.split("=", 1)[1].strip()
if not oc:
    sys.exit("LAW_API_KEY 없음")

CASE_RE = re.compile(r"\b(\d{2,4})(다|도|마|바|카|누|후|므|타|파|허|하|그|모|두|재다|재두)(\d{2,6})\b")

def collect(files):
    cnt = Counter()
    for f in files:
        txt = Path(f).read_text(encoding="utf-8", errors="ignore")
        for m in CASE_RE.finditer(txt):
            cnt[f"{m.group(1)}{m.group(2)}{m.group(3)}"] += 1
    return cnt

def verify(caseno):
    """DRF prec 검색 → 반환 사건번호에 정확일치 있으면 True."""
    qs = urllib.parse.urlencode({"OC": oc, "target": "prec", "type": "XML",
                                  "query": caseno, "display": "20"})
    url = f"https://www.law.go.kr/DRF/lawSearch.do?{qs}"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            raw = r.read().decode("utf-8", "ignore")
        root = ET.fromstring(raw)
        nums = [e.text.strip() for e in root.iter("사건번호") if e.text]
        # 정확 일치(공백/구두점 무시)
        norm = lambda s: re.sub(r"\s|·|,", "", s)
        hit = any(norm(caseno) in norm(n) for n in nums)
        return hit, len(nums)
    except Exception as e:
        return None, f"ERR:{type(e).__name__}"

def main():
    pilot = sorted(OCR.glob("쟁점노트_가족법_llamaparse_p*.md"))
    allf = sorted(OCR.glob("민소사례_llamaparse_p*.md")) + \
           sorted(OCR.glob("쟁점노트_소송집행_llamaparse_p*.md")) + pilot
    pilot_cases = collect(pilot)
    all_cases = collect(allf)
    # 샘플: 파일럿(가족법) 상위 10 + 전체 고빈도 10 + 전체 저빈도 5
    top_all = [c for c, _ in all_cases.most_common(10)]
    rare = [c for c, n in all_cases.items() if n == 1][:5]
    sample = list(dict.fromkeys([c for c, _ in pilot_cases.most_common(10)] + top_all + rare))
    print(f"유니크 사건번호: 가족법 {len(pilot_cases)} / 전체(3종) {len(all_cases)}")
    print(f"샘플 {len(sample)}건 검증 (DRF target=prec)\n" + "=" * 55)
    found = notfound = err = 0
    for c in sample:
        hit, info = verify(c)
        if hit is None:
            tag, err = f"[ERR {info}]", err + 1
        elif hit:
            tag, found = f"[OK 실존·일치 (검색 {info}건)]", found + 1
        else:
            tag, notfound = f"[미발견 (검색 {info}건) — 미수록 or 위조]", notfound + 1
        print(f"  {c:<14} {tag}")
        time.sleep(0.4)
    print("=" * 55)
    print(f"확정 실존: {found} / 미발견: {notfound} / 오류: {err}  (샘플 {len(sample)})")
    if found + notfound:
        print(f"표본 실존율(미발견=위조 가정 상한): {found}/{found+notfound} = {found*100//(found+notfound)}%")

if __name__ == "__main__":
    main()
