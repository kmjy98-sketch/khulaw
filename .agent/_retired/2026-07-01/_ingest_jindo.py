# -*- coding: utf-8 -*-
"""진도 보드 내보내기(JSON) → Claude 반영.
보드 [JSON 내보내기] 파일을 6.진도관리/백업/(또는 6.진도관리/)에 저장한 뒤 실행:
  python .agent/scripts/_ingest_jindo.py            # 최신 export 자동탐색
  python .agent/scripts/_ingest_jindo.py "경로.json"
산출:
  .agent/state/진도_현황.json  (기계용: 단원별 회독/선택/사례/기록 + 요약 + 최근로그)
  6.진도관리/진도_현황.md       (사람용 표)
  .agent/state/progress.json   에 '보드연동' 요약 블록 갱신(기존 구조 보존)
"""
import json, re, sys, glob, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

ROOT = VAULT_ROOT
HTML = os.path.join(ROOT, "6.진도관리", "진도_board.html")
STATE = os.path.join(ROOT, ".agent", "state")
OUT_JSON = os.path.join(STATE, "진도_현황.json")
OUT_MD = os.path.join(ROOT, "6.진도관리", "진도_현황.md")
PROG = os.path.join(STATE, "progress.json")


def load_board():
    t = open(HTML, encoding="utf-8").read()
    m = t[t.index("const BOARD=") + len("const BOARD="):]
    m = m[:m.index("};\nconst ALL") + 1]
    return json.loads(m)


def find_export(arg):
    if arg and os.path.exists(arg):
        return arg
    pats = [os.path.join(ROOT, "6.진도관리", "백업", "*.json"),
            os.path.join(ROOT, "6.진도관리", "*.json"),
            os.path.join(ROOT, "6.진도관리", "data", "*export*.json")]
    cand = []
    for p in pats:
        cand += glob.glob(p)
    cand = [c for c in cand if os.path.basename(c) not in ("진도_소단원_master.csv",)]
    if not cand:
        return None
    return max(cand, key=os.path.getmtime)


def main():
    board = load_board()
    exp_path = find_export(sys.argv[1] if len(sys.argv) > 1 else None)
    if not exp_path:
        print("export JSON 없음. 보드 [JSON 내보내기] 파일을 6.진도관리/백업/에 저장 후 다시 실행.")
        sys.exit(1)
    exp = json.load(open(exp_path, encoding="utf-8"))
    R = exp.get("회독", {}); S = exp.get("선택", {}); C = exp.get("사례", {}); G = exp.get("기록", {})
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    def stat(keys):
        n = len(keys); t1 = sum(1 for k in keys if R.get(k, 0) > 0)
        rs = sum(R.get(k, 0) for k in keys); ss = sum(S.get(k, 0) for k in keys)
        cs = sum(C.get(k, 0) for k in keys); gs = sum(G.get(k, 0) for k in keys)
        return {"단원": n, "1회독+": t1, "완료율": round(t1 / n * 100) if n else 0,
                "평균회독": round(rs / n, 2) if n else 0, "선택": ss, "사례": cs, "기록": gs}

    all_keys, subj_sum, units = [], {}, {}
    for subj, mids in board.items():
        sk = []
        units[subj] = {}
        for mid, us in mids.items():
            units[subj][mid] = {}
            for u in us:
                k = f"{subj}|{mid}|{u}"
                sk.append(k); all_keys.append(k)
                units[subj][mid][u] = {"회독": R.get(k, 0), "선택": S.get(k, 0), "사례": C.get(k, 0), "기록": G.get(k, 0)}
        subj_sum[subj] = stat(sk)

    naesin = exp.get("내신_학기별", {})
    naesin_cnt = {s: len(v) for s, v in naesin.items()}
    banghak_cnt = len(exp.get("방학_단원", []))
    logs = exp.get("기록로그", [])[-30:]

    out = {"반영": now, "출처": os.path.basename(exp_path), "보드갱신": exp.get("updated", ""),
           "요약": {"전체": stat(all_keys), "과목": subj_sum},
           "내신_학기별": naesin_cnt, "방학단원수": banghak_cnt,
           "단원": units, "최근로그": logs}
    os.makedirs(STATE, exist_ok=True)
    json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 사람용 md
    L = [f"# 진도 현황 (보드 연동) — 반영 {now}",
         f"> 출처 `{os.path.basename(exp_path)}` (보드갱신 {exp.get('updated','')}). 회독·선택/사례/기록 문제수. 기계용: `.agent/state/진도_현황.json`", ""]
    e = out["요약"]["전체"]
    L.append(f"## 전체\n- 단원 {e['단원']} · 1회독+ {e['1회독+']} (완료율 {e['완료율']}%) · 평균 {e['평균회독']}회독 · 문제 선{e['선택']} 사{e['사례']} 기{e['기록']}\n")
    L.append("## 과목별\n| 과목 | 단원 | 1회독+ | 완료율 | 평균회독 | 선택 | 사례 | 기록 |\n|---|---:|---:|---:|---:|---:|---:|---:|")
    for s, v in subj_sum.items():
        L.append(f"| {s} | {v['단원']} | {v['1회독+']} | {v['완료율']}% | {v['평균회독']} | {v['선택']} | {v['사례']} | {v['기록']} |")
    L.append("\n## 내신(학기별 단원 수)\n- " + " / ".join(f"{s}:{c}" for s, c in naesin_cnt.items()) + f"\n## 방학 단원: {banghak_cnt}")
    if logs:
        L.append("\n## 최근 기록(시점)")
        for r in reversed(logs):
            L.append(f"- {r[0]} · {r[1]}>{r[2]}>{r[3]} · {r[4]} {r[5]}")
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(L) + "\n")

    # progress.json 보드연동 블록(기존 구조 보존)
    try:
        prog = json.load(open(PROG, encoding="utf-8-sig"))
    except Exception:
        prog = {}
    prog["보드연동"] = {"반영": now, "출처": os.path.basename(exp_path),
                     "과목별": {s: {"평균회독": v["평균회독"], "완료율": v["완료율"],
                                "선택": v["선택"], "사례": v["사례"], "기록": v["기록"]} for s, v in subj_sum.items()}}
    json.dump(prog, open(PROG, "w", encoding="utf-8"), ensure_ascii=False, indent=4)

    print(f"반영 완료 · 전체 {e['단원']}단원 1회독+{e['1회독+']}({e['완료율']}%) 평균{e['평균회독']}회 · 문제 선{e['선택']}/사{e['사례']}/기{e['기록']}")
    print(f"  → {OUT_JSON}")
    print(f"  → {OUT_MD}")
    print(f"  → progress.json 보드연동 블록 갱신")


if __name__ == "__main__":
    main()
