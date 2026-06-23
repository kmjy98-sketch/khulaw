# -*- coding: utf-8 -*-
"""
anchor_verify_batch.py — v4 카드 사건번호 일괄 검증 (국가법령정보센터 Open API)
- 입력: .agent/state/anchor_verify_targets.json (고유 사건번호 목록)
- 대법원 등 → target=prec / 헌재(헌가·헌나·헌마·헌바 등) → target=detc
- verified = 검색결과의 '사건번호' 필드가 질의 번호와 정확히 일치(토큰 단위)할 때만.
  total>0이어도 필드 불일치면 ambiguous (인용 문서 오탐 방지). total==0 → not_found.
- 출력: .agent/state/anchor_verify_results.jsonl (증분, 재실행 시 이어서) + 요약 md
- API 예의: 0.15s 간격, 3회 재시도. usage: python anchor_verify_batch.py [--limit N]
"""
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

STATE = Path(vp(".agent", "state"))
TARGETS = STATE / "anchor_verify_targets.json"
RESULTS = STATE / "anchor_verify_results.jsonl"
SUMMARY = STATE / "anchor_verify_summary.md"
ENV = Path(vp(".agent", "skills", "korean-law-mcp", ".env"))
BASE = "https://www.law.go.kr/DRF/lawSearch.do"
HUN = re.compile(r"헌[가나다라마바사아]")


def api_key():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("LAW_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("LAW_API_KEY 없음")


def check(sess, key, case_no):
    target = "detc" if HUN.search(case_no) else "prec"
    root = None
    for attempt in range(3):
        try:
            r = sess.get(BASE, params={
                "OC": key, "target": target, "type": "XML",
                "query": case_no, "display": 20, "page": 1,
            }, timeout=30)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            break
        except Exception as e:
            if attempt == 2:
                return {"status": "error", "target": target, "detail": str(e)[:120]}
            time.sleep(1 + attempt * 2)
    total = root.findtext(".//totalCnt") or "0"
    matches = []
    for el in root.iter():
        no = el.findtext("사건번호") if len(el) else None
        if not no:
            continue
        tokens = [t.strip() for t in re.split(r"[,·;/]|\(병합\)|\(반소\)", no.replace(" ", "")) if t.strip()]
        if case_no in tokens or no.replace(" ", "") == case_no:
            matches.append({
                "사건번호": no.strip(),
                "선고일자": (el.findtext("선고일자") or el.findtext("종국일자") or "").strip(),
                "법원": (el.findtext("법원명") or "헌법재판소").strip(),
                "사건명": (el.findtext("사건명") or "").strip()[:60],
            })
    if matches:
        return {"status": "verified", "target": target, "match": matches[0]}
    if total == "0":
        return {"status": "not_found", "target": target}
    return {"status": "ambiguous", "target": target, "total": int(total)}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    key = api_key()
    targets = json.loads(TARGETS.read_text(encoding="utf-8"))
    done = set()
    if RESULTS.exists():
        for line in RESULTS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                if rec["status"] != "error":  # error는 재실행 시 재시도
                    done.add(rec["case_no"])
    todo = [t for t in targets if t not in done]
    if limit:
        todo = todo[:limit]
    print(f"대상 {len(targets)} / 완료 {len(done)} / 이번 실행 {len(todo)}")
    sess = requests.Session()
    counts = {}
    with RESULTS.open("a", encoding="utf-8") as out:
        for i, no in enumerate(todo, 1):
            res = check(sess, key, no)
            res["case_no"] = no
            out.write(json.dumps(res, ensure_ascii=False) + "\n")
            counts[res["status"]] = counts.get(res["status"], 0) + 1
            if i % 200 == 0:
                out.flush()
                print(f"  {i}/{len(todo)} {counts}", flush=True)
            time.sleep(0.15)
    print("결과:", counts)
    # 전체 요약 재계산
    allres = [json.loads(l) for l in RESULTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    tally = {}
    for r in allres:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    lines = ["# 사건번호 검증 요약 (anchor_verify_batch.py)", "",
             f"- 전체 대상: {len(targets)} / 처리: {len(allres)}",
             f"- 집계: {tally}", "", "## not_found (OCR 손상 의심 — 카드 검토 필요)"]
    lines += [f"- {r['case_no']} ({r['target']})" for r in allres if r["status"] == "not_found"]
    lines += ["", "## ambiguous (검색은 되나 필드 불일치 — 수동 확인)"]
    lines += [f"- {r['case_no']} ({r['target']}, total={r.get('total')})" for r in allres if r["status"] == "ambiguous"]
    SUMMARY.write_text("\n".join(lines), encoding="utf-8")
    print(f"요약: {SUMMARY}")


if __name__ == "__main__":
    main()
