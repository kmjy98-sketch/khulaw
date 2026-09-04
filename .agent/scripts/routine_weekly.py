# -*- coding: utf-8 -*-
"""주간 루틴(T0, LLM 무호출): lint 정합점검 + 카드·사례 카운트 스냅샷 + 로그. 일요일 실행.
산출: routine_log.jsonl 1행 + 루틴_현황.md 갱신(주간 행). 발견사항은 사용자가 세션에서 '주간리뷰'로 종합."""
import json, os, re, subprocess, sys, glob
from datetime import datetime
ROOT = r"E:\법학볼트"
os.chdir(ROOT)
log = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M"), "routine": "weekly"}
try:
    r = subprocess.run([sys.executable, r".agent\scripts\lint.py"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=600)
    m = re.search(r"총 \d+건[^\n]*", (r.stdout or ""))
    log["lint"] = m.group(0) if m else ("OK" if r.returncode == 0 else "FAIL")
except Exception as e:
    log["lint"] = "ERR:" + repr(e)[:80]
try:
    cardver = sum(1 for s in ["민법","민사소송법","헌법","형법총론","형법각론","행정법"]
                  for f in glob.glob("sync/위키/%s/*.md" % s)
                  if not os.path.basename(f).startswith("_")
                  and re.search(r'(?m)^카드검증:\s*["\x27]?완료', open(f, encoding="utf-8").read()))
    ncase = sum(len(glob.glob("sync/위키/사례/%s/*.md" % s)) for s in ["민법","민사소송법","헌법","형법총론","형법각론"])
    nauth = sum(1 for s in ["민법","민사소송법","헌법","형법총론","형법각론"]
                for f in glob.glob("sync/위키/사례/%s/*.md" % s)
                if re.search(r"(?m)^원문성:\s*검증완료", open(f, encoding="utf-8").read()))
    log["카드검증"] = cardver; log["사례노트"] = ncase; log["원문성검증"] = nauth
except Exception as e:
    log["카운트"] = repr(e)[:80]
# 완료문서 보관 후보 스캔(#42): _meta 정본 화이트리스트 외 + 9.작업중/클로드 14일 경과분 → 보고만(이동은 사용자 확인)
try:
    from datetime import timedelta
    KEEP = {"_INDEX.md", "CLAUDE_변경이력.md", "DECISIONS.md", "PROJECT_CONTEXT.md",
            "OCR_텍스트_복원_가이드.md", "frontmatter_property_schema_2026-06-22.md",
            "개선설계_모델티어링_복습3루프_2026-07-01.md", "개선설계_문서보관층_모델라우팅_2026-07-02.md",
            "카드_사례_설계확정_2026-06-28.md", "판례탐색_전략_2026-06-20.md"}
    import time
    now = time.time()
    cand = []
    for f in glob.glob(r"sync\수신함\*.md") + glob.glob(r"sync\수신함\웹클립\*.md"):
        b = os.path.basename(f)
        if b != "_README.md" and now - os.path.getmtime(f) > 14 * 86400:
            cand.append("수신함/" + b)
    for f in glob.glob(r"9.작업중/클로드\*.md"):
        b = os.path.basename(f)
        if b in KEEP or b in ("_README.md", "_INDEX.md"):
            continue
        if now - os.path.getmtime(f) > 14 * 86400:
            cand.append("9.작업중/클로드/" + b)
    log["보관후보"] = cand[:20]
    if cand:
        with open(r"6.진도관리\루틴_현황.md", "a", encoding="utf-8") as f:
            f.write("\n## 보관 후보 (완료·14일 경과 — 확인 후 문서보관 이동)\n"
                    + "\n".join("- " + c for c in cand) + "\n")
except Exception as e:
    log["보관스캔"] = repr(e)[:80]

# Anki 컬렉션 오프사이트 백업(2026-07-07 감사 P0: FSRS 정본이 C: 단일 디스크에만 존재 → Drive 동기화 경로로 주기 복사)
try:
    import shutil
    src = os.path.join(os.environ.get("APPDATA", ""), "Anki2", "사용자 1", "collection.anki2")
    if os.path.exists(src):
        dstdir = os.path.join(ROOT, "outputs", "anki", "collection_backup")
        os.makedirs(dstdir, exist_ok=True)
        dst = os.path.join(dstdir, "collection_%s.anki2" % datetime.now().strftime("%Y-%m-%d"))
        shutil.copy2(src, dst)
        log["anki백업"] = os.path.basename(dst)
except Exception as e:
    log["anki백업"] = "ERR:" + repr(e)[:80]

with open(r".agent\state\routine_log.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(log, ensure_ascii=False) + "\n")
print("weekly routine done:", log)
