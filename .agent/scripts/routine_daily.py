# -*- coding: utf-8 -*-
"""일일 루틴(T0, LLM 무호출): 드릴 세션 구성 + 현황 로그. Windows 작업 스케줄러로 매일 실행.
산출: 6.진도관리/오늘_드릴.md 갱신 + .agent/state/routine_log.jsonl 1행 + 6.진도관리/루틴_현황.md 갱신."""
import json, os, re, subprocess, sys, glob
from datetime import datetime
ROOT = r"E:\법학볼트"
os.chdir(ROOT)
log = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M"), "routine": "daily"}
try:
    r = subprocess.run([sys.executable, r".agent\skills\daily-drill\scripts\build_session.py", "--n", "3"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    log["build_session"] = "OK" if r.returncode == 0 else "FAIL:" + (r.stderr or "")[-120:]
except Exception as e:
    log["build_session"] = "ERR:" + repr(e)[:100]
# 진도 스냅샷(집계만)
try:
    ver = rem = 0
    weak = 0
    for s in ["민법", "민사소송법", "헌법", "형법총론", "형법각론", "행정법", "민사집행법"]:
        for f in glob.glob("sync/위키/%s/*.md" % s):
            if os.path.basename(f).startswith("_"):
                continue
            t = open(f, encoding="utf-8").read()
            if re.search(r"(?m)^회독:\s*[1-9]", t):
                ver += 1
            else:
                rem += 1
            if re.search(r"(?m)^약점:\s*true", t):
                weak += 1
    log["회독1이상"] = ver; log["회독0"] = rem; log["약점"] = weak
except Exception as e:
    log["스냅샷"] = repr(e)[:80]
with open(r".agent\state\routine_log.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(log, ensure_ascii=False) + "\n")
# 사람용 현황(최근 7행)
rows = open(r".agent\state\routine_log.jsonl", encoding="utf-8").read().strip().split("\n")[-7:]
L = ["# 루틴 현황 (자동 갱신 — 확인용)", "", "| 시각 | 루틴 | 결과 | 회독1+ | 약점 |", "|---|---|---|---|---|"]
for row in rows:
    try:
        d = json.loads(row)
        L.append("| %s | %s | %s | %s | %s |" % (d.get("ts"), d.get("routine"),
                 d.get("build_session", d.get("lint", "-"))[:24], d.get("회독1이상", "-"), d.get("약점", "-")))
    except Exception:
        pass
open(r"6.진도관리\루틴_현황.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("daily routine done:", log)
