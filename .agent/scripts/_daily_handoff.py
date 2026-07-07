# -*- coding: utf-8 -*-
"""일일 핸드오프 자동 생성 — 매일 03:00 루틴. 2026-06-27.
위키 재구축 현황 + 카드 감사 결과 + Bases/닫힌루프 상태 + 다음단계 큐를 집계해
9.작업중/클로드/핸드오프_자동_{YYYY-MM-DD}.md 로 기록. 감사 결과를 핸드오프에 '연결'.
파이썬-PDF 미사용(상태 .md/.json만 집계)."""
import glob, json, os, re, sys
from datetime import datetime
if sys.stdout is None:  # pythonw(비콘솔) 가드 — 2026-07-07 감사: 도입 후 미산출 원인 1
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
else:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"E:\법학볼트"; WIKI = os.path.join(ROOT, "sync", "위키"); STATE = os.path.join(ROOT, ".agent", "state")
NOISE = {"쟁점", "제목", "MOC", "_MOC"}

def moc_targets(sd):
    t = set()
    for m in glob.glob(os.path.join(sd, "_*목차*.md")):
        for ln in open(m, encoding="utf-8").read().splitlines():
            if ln.lstrip().startswith(">"): continue
            for x in re.findall(r"\[\[([^\]]+)\]\]", ln):
                x = x.strip()
                if x and not x.startswith("_") and x not in NOISE: t.add(x)
    return t

# 1) 위키 재구축 현황(과목별 검증완료)
wiki = []
for s in sorted([d for d in os.listdir(WIKI) if os.path.isdir(os.path.join(WIKI, d)) and d != "쟁점"]):
    sd = os.path.join(WIKI, s); tgt = len(moc_targets(sd))
    done = 0
    for f in glob.glob(os.path.join(sd, "*.md")):
        if os.path.basename(f).startswith("_"): continue
        try:
            if "검증완료" in re.search(r"(?m)^상태:\s*(.+)$", open(f, encoding="utf-8").read()).group(1): done += 1
        except Exception: pass
    wiki.append((s, tgt, done))

# 2) 카드 감사
card = {}
try: card = json.load(open(os.path.join(STATE, "card_audit_summary.json"), encoding="utf-8")).get("과목", {})
except Exception: pass

# 3) Bases/닫힌루프 상태
bases = bool(glob.glob(os.path.join(WIKI, "**", "*.base"), recursive=True))
has_prop = bool(glob.glob(os.path.join(WIKI, "민법", "*.md")) and
                any("회독:" in open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(WIKI, "민법", "*.md"))[:3]))
drill = os.path.getsize(os.path.join(STATE, "drill_log.jsonl")) if os.path.exists(os.path.join(STATE, "drill_log.jsonl")) else 0

# 4) 작성
now = datetime.now()
L = [f"---\ntype: 핸드오프(자동)\n일자: {now:%Y-%m-%d %H:%M}\n생성: _daily_handoff.py (03:00 루틴)\n---", ""]
L.append(f"# 자동 핸드오프 {now:%Y-%m-%d}\n")
L.append("## 1. 위키 재구축 (논점 원문보존)")
L.append("| 과목 | 목표 | 검증완료 |\n|---|---:|---:|")
tt = td = 0
for s, t, d in wiki:
    L.append(f"| {s} | {t} | {d} |"); tt += t; td += d
L.append(f"| **합계** | **{tt}** | **{td}** |\n")
L.append("## 2. 카드 감사 (전수 461 누락) — 상세 `.agent/state/cardaudit_집계.md`")
L.append("| 과목 | 감사 | 총누락 | 평균 | 카드없음 | 권고 |\n|---|---:|---:|---:|---:|---|")
for k, v in card.items():
    L.append(f"| {k} | {v.get('감사','?')} | {v.get('총누락','-')} | {v.get('평균','-')} | {v.get('카드없음','-')} | {v.get('권고','')} |")
L.append("")
L.append("## 3. 옵시디언 Bases / 닫힌루프")
L.append(f"- .base 존재: {'예' if bases else '아니오(미구축)'} · 논점노트 진도속성: {'있음' if has_prop else '없음'} · drill_log: {drill}B")
L.append(f"- 핸드오프(상세): `9.작업중/클로드/핸드오프_옵시디언Bases_닫힌루프_2026-06-27.md`\n")
L.append("## 4. 다음 단계 큐")
L.append("- 카드: 행정법 대량신규(0%) + 나머지 누락(13~36%) 부분개선.")
L.append("- Bases/닫힌루프: 논점노트 진도속성 배선 → 진도보드.base → 진도_state 시드 → 약점·drill·SRS 논점키 → board_server 은퇴.")
L.append("- 점검: `python .agent/scripts/_rebuild_status.py` (위키 완료/미검증).")
L.append("")
L.append("## 5. 참고 파일 (마커·감사·로그 — 다음 세션이 자동 참고)")
L.append("- 위키 진행·검증 현황(마커): `.agent/state/rebuild_진행현황.md` · 재계산 `.agent/scripts/_rebuild_status.py`")
L.append("- 카드 감사(전수461): `.agent/state/card_audit_summary.json` + 집계 `.agent/state/cardaudit_집계.md` + 배치별 `.agent/state/cardaudit/`")
L.append("- Bases/닫힌루프 핸드오프: `9.작업중/클로드/핸드오프_옵시디언Bases_닫힌루프_2026-06-27.md`")
L.append("- 정리(이동) 기록: `_trash/{날짜}/*/_MANIFEST.md` · 은퇴: `.agent/_retired/{날짜}/_RETIRED_INDEX.md`")
L.append("- 룰 정본: `CLAUDE.md`(#50 위키2층·#45-C 재개가능 검증 fan-out·#16-D 분할) · 메모리 [[law-vault-target-architecture]]")
out = os.path.join(ROOT, "9.작업중", "클로드", f"핸드오프_자동_{now:%Y-%m-%d}.md")  # 경로 오기 수정(sync/ 접두 제거, 2026-07-07 감사)
open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print(f"[작성] {out}")
