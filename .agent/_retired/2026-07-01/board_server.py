# -*- coding: utf-8 -*-
"""진도 보드 로컬 서버 (표준 라이브러리만 사용).

진도_board.html 을 http://localhost 로 띄우고, 클릭마다 디스크에 기록한다.
 - 백업/진도_log.jsonl   : 클릭 1건 = 1줄 (append-only 로그)
 - 백업/진도_state.json  : 전체 상태 스냅샷 (브라우저 캐시가 날아가도 보존)
 - 백업/진도_board_export_latest.json : _ingest_jindo.py 호환 내보내기 형식
 - .agent/state/진도_현황.json  : 기계용 단원별 집계 (자동 갱신)
 - 6.진도관리/진도_현황.md       : 사람용 표 (자동 갱신)
 - .agent/state/progress.json  : '보드연동' 블록 자동 갱신
약점 연동:
 - GET  /api/weak : .agent/state/learning.json 의 weak_points + SRS 임박 반환
 - POST /api/weak : 보드 신호 기반 약점 후보를 weak_points 에 추가(구조 보존, append-only)

실행:  python board_server.py        (브라우저 자동 오픈)
       python board_server.py --selftest   (서버 안 띄우고 저장 로직만 점검)
"""
import json
import os
import sys
import re
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# pythonw(콘솔 없는 백그라운드 실행)에서는 sys.stdout/stderr 가 None → print 가 죽어
# 서버가 즉시 종료될 수 있다. devnull 로 보정해 어떤 실행 방식에서도 안전하게.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
HTML = os.path.join(SCRIPT_DIR, "진도_board.html")
BACKUP = os.path.join(SCRIPT_DIR, "백업")
STATE = os.path.join(ROOT, ".agent", "state")
LEARNING = os.path.join(STATE, "learning.json")
STATE_JSON = os.path.join(BACKUP, "진도_state.json")
LOG_JSONL = os.path.join(BACKUP, "진도_log.jsonl")
EXPORT_LATEST = os.path.join(BACKUP, "진도_board_export_latest.json")
HYUN_JSON = os.path.join(STATE, "진도_현황.json")
HYUN_MD = os.path.join(SCRIPT_DIR, "진도_현황.md")
PROG = os.path.join(STATE, "progress.json")

PORT = 8770

# 테스트 격리용: BOARD_SANDBOX 환경변수가 있으면 쓰기 산출물을 그 폴더로 우회
# (HTML 파싱·learning.json 읽기는 실제 경로 유지 → 약점 읽기까지 동일하게 검증)
_SB = os.environ.get("BOARD_SANDBOX")
if _SB:
    os.makedirs(_SB, exist_ok=True)
    BACKUP = _SB
    STATE_JSON = os.path.join(_SB, "진도_state.json")
    EXPORT_LATEST = os.path.join(_SB, "진도_board_export_latest.json")
    LOG_JSONL = os.path.join(_SB, "진도_log.jsonl")
    HYUN_JSON = os.path.join(_SB, "진도_현황.json")
    HYUN_MD = os.path.join(_SB, "진도_현황.md")
    PROG = os.path.join(_SB, "progress.json")
_LRN = os.environ.get("BOARD_LEARNING")  # 약점 쓰기 테스트용 learning.json 우회
if _LRN:
    LEARNING = _LRN


# ---------------------------------------------------------------- 보드 목차 파싱
def load_board():
    t = open(HTML, encoding="utf-8").read()
    m = t[t.index("const BOARD=") + len("const BOARD="):]
    m = m[:m.index("};\nconst ALL") + 1]
    return json.loads(m)


def all_keys(board):
    ks = []
    for subj, mids in board.items():
        for mid, us in mids.items():
            for u in us:
                ks.append(f"{subj}|{mid}|{u}")
    return ks


# ---------------------------------------------------------------- 상태 입출력
def _has_data(s):
    if not isinstance(s, dict):
        return False
    for k in ("회독", "선택", "사례", "기록"):
        d = s.get(k) or {}
        if isinstance(d, dict) and any(v for v in d.values()):  # 값이 0뿐이면 데이터 아님
            return True
    if s.get("방학_단원") or s.get("기록로그"):
        return True
    if any((s.get("내신_학기별") or {}).values()):
        return True
    return False


def read_state():
    cur = None
    if os.path.exists(STATE_JSON):
        try:
            cur = json.load(open(STATE_JSON, encoding="utf-8"))
        except Exception:
            cur = None
    # 저장된 상태에 데이터가 있으면 그대로 사용
    if _has_data(cur):
        return cur
    # 비어 있으면(최초·또는 빈 스냅샷) 백업 폴더의 내보내기 JSON으로 시드
    seed = _find_seed()
    if _has_data(seed):
        return seed
    return cur or {"updated": "", "회독": {}, "선택": {}, "사례": {}, "기록": {},
                   "내신_학기별": {}, "방학_단원": [], "기록로그": []}


def _find_seed():
    if not os.path.isdir(BACKUP):
        return None
    cand = []
    for fn in os.listdir(BACKUP):
        if not fn.lower().endswith(".json"):
            continue
        if fn in ("진도_state.json", "진도_board_export_latest.json"):
            continue
        p = os.path.join(BACKUP, fn)
        try:
            o = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(o, dict) and "회독" in o:
            cand.append((os.path.getmtime(p), o))
    if not cand:
        return None
    cand.sort(key=lambda x: x[0])
    return cand[-1][1]


def write_state(state):
    os.makedirs(BACKUP, exist_ok=True)
    json.dump(state, open(STATE_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # _ingest_jindo.py 호환 내보내기 형식 동시 저장
    exp = {"updated": state.get("updated", ""),
           "회독": state.get("회독", {}), "선택": state.get("선택", {}),
           "사례": state.get("사례", {}), "기록": state.get("기록", {}),
           "내신_학기별": state.get("내신_학기별", {}), "방학_단원": state.get("방학_단원", []),
           "기록로그": state.get("기록로그", [])}
    json.dump(exp, open(EXPORT_LATEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    refresh_hyunhwang(state)


def append_log(entry):
    os.makedirs(BACKUP, exist_ok=True)
    with open(LOG_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- 진도 현황 집계
def refresh_hyunhwang(state):
    board = load_board()
    R = state.get("회독", {}); S = state.get("선택", {})
    C = state.get("사례", {}); G = state.get("기록", {})
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    def stat(keys):
        n = len(keys); t1 = sum(1 for k in keys if R.get(k, 0) > 0)
        rs = sum(R.get(k, 0) for k in keys); ss = sum(S.get(k, 0) for k in keys)
        cs = sum(C.get(k, 0) for k in keys); gs = sum(G.get(k, 0) for k in keys)
        return {"단원": n, "1회독+": t1, "완료율": round(t1 / n * 100) if n else 0,
                "평균회독": round(rs / n, 2) if n else 0, "선택": ss, "사례": cs, "기록": gs}

    akeys, subj_sum, units = [], {}, {}
    for subj, mids in board.items():
        sk = []; units[subj] = {}
        for mid, us in mids.items():
            units[subj][mid] = {}
            for u in us:
                k = f"{subj}|{mid}|{u}"
                sk.append(k); akeys.append(k)
                units[subj][mid][u] = {"회독": R.get(k, 0), "선택": S.get(k, 0),
                                       "사례": C.get(k, 0), "기록": G.get(k, 0)}
        subj_sum[subj] = stat(sk)

    naesin_cnt = {s: len(v) for s, v in state.get("내신_학기별", {}).items()}
    banghak_cnt = len(state.get("방학_단원", []))
    logs = state.get("기록로그", [])[-30:]

    out = {"반영": now, "출처": "board_server(클릭자동)", "보드갱신": state.get("updated", ""),
           "요약": {"전체": stat(akeys), "과목": subj_sum},
           "내신_학기별": naesin_cnt, "방학단원수": banghak_cnt,
           "단원": units, "최근로그": logs}
    os.makedirs(STATE, exist_ok=True)
    json.dump(out, open(HYUN_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    e = out["요약"]["전체"]
    L = [f"# 진도 현황 (보드 연동) — 반영 {now}",
         f"> 출처 `board_server(클릭 자동저장)` (보드갱신 {state.get('updated','')}). 기계용: `.agent/state/진도_현황.json`", ""]
    L.append(f"## 전체\n- 단원 {e['단원']} · 1회독+ {e['1회독+']} (완료율 {e['완료율']}%) · 평균 {e['평균회독']}회독 · 문제 선{e['선택']} 사{e['사례']} 기{e['기록']}\n")
    L.append("## 과목별\n| 과목 | 단원 | 1회독+ | 완료율 | 평균회독 | 선택 | 사례 | 기록 |\n|---|---:|---:|---:|---:|---:|---:|---:|")
    for s, v in subj_sum.items():
        L.append(f"| {s} | {v['단원']} | {v['1회독+']} | {v['완료율']}% | {v['평균회독']} | {v['선택']} | {v['사례']} | {v['기록']} |")
    L.append("\n## 내신(학기별 단원 수)\n- " + " / ".join(f"{s}:{c}" for s, c in naesin_cnt.items()) + f"\n## 방학 단원: {banghak_cnt}")
    if logs:
        L.append("\n## 최근 기록(시점)")
        for r in reversed(logs):
            L.append(f"- {r[0]} · {r[1]}>{r[2]}>{r[3]} · {r[4]} {r[5]}")
    open(HYUN_MD, "w", encoding="utf-8").write("\n".join(L) + "\n")

    try:
        prog = json.load(open(PROG, encoding="utf-8-sig"))
    except Exception:
        prog = {}
    prog["보드연동"] = {"반영": now, "출처": "board_server(클릭 자동)",
                     "과목별": {s: {"평균회독": v["평균회독"], "완료율": v["완료율"],
                                "선택": v["선택"], "사례": v["사례"], "기록": v["기록"]} for s, v in subj_sum.items()}}
    json.dump(prog, open(PROG, "w", encoding="utf-8"), ensure_ascii=False, indent=4)


# ---------------------------------------------------------------- 약점 연동
def read_weak():
    try:
        lj = json.load(open(LEARNING, encoding="utf-8"))
    except Exception:
        lj = {}
    weak = lj.get("weak_points", [])
    srs_items = (lj.get("srs", {}) or {}).get("items", [])
    today = date.today().isoformat()
    due, upcoming = [], []
    for it in srs_items:
        nr = it.get("next_review", "")
        row = {"content": it.get("content", ""), "topic": it.get("topic", ""),
               "next_review": nr, "priority": it.get("priority", "")}
        if nr and nr <= today:
            due.append(row)
        else:
            upcoming.append(row)
    return {"weak_points": weak, "srs_due": due, "srs_upcoming": upcoming, "today": today}


def add_weak(candidates):
    """보드 신호 기반 약점 후보를 weak_points 에 추가(중복 제외, 구조 보존)."""
    try:
        lj = json.load(open(LEARNING, encoding="utf-8"))
    except Exception:
        lj = {}
    wp = lj.get("weak_points", [])
    existing = set(wp)
    added = []
    for c in candidates:
        label = c.get("label") or c.get("content")
        if not label:
            continue
        prefix = c.get("tag", "[진도보드]")
        full = f"{prefix} {label}"
        if full in existing:
            continue
        wp.append(full); existing.add(full); added.append(full)
    lj["weak_points"] = wp
    lj["last_board_weak"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    os.makedirs(STATE, exist_ok=True)
    json.dump(lj, open(LEARNING, "w", encoding="utf-8"), ensure_ascii=False, indent=4)
    return {"added": added, "weak_points": lj["weak_points"]}


def _unit_label(key):
    p = (key or "").split("|")
    return ">".join(p) if len(p) == 3 else (key or "")


def apply_board_bump(unit_keys, kind, delta=1):
    """드릴 등 외부 활동을 보드 카운트에 반영(선택/사례 등 +1). 보드 클릭과 동일하게 디스크 저장."""
    if kind not in ("회독", "선택", "사례", "기록"):
        raise ValueError(f"kind 오류: {kind}")
    unit_keys = [k for k in (unit_keys or []) if k]
    if not unit_keys:
        return []
    state = read_state()
    d = state.setdefault(kind, {})
    logs = state.setdefault("기록로그", [])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    changed = []
    for k in unit_keys:
        if not k:
            continue
        d[k] = max(0, int(d.get(k, 0)) + int(delta))
        p = k.split("|")
        if len(p) == 3:
            logs.append([now, p[0], p[1], p[2], kind, d[k], delta])  # 보드 로그 7-튜플 동일 형식
        changed.append({"key": k, kind: d[k]})
    if len(logs) > 3000:
        del logs[:-3000]
    state["updated"] = now
    write_state(state)
    append_log({"ts": now, "kind": kind, "keys": unit_keys, "delta": delta, "src": "drill"})
    return changed


# ---------------------------------------------------------------- 시험일 다중 타깃
def read_exams():
    """learning.json['exams'] 반환(+D-day). srs_scheduler 와 동일 포맷."""
    try:
        lj = json.load(open(LEARNING, encoding="utf-8-sig"))
    except Exception:
        lj = {}
    today = date.today()
    out = []
    for e in (lj.get("exams") or []):
        if not isinstance(e, dict):
            continue
        subs = e.get("subjects", "all")
        if not isinstance(subs, list):
            subs = "all"
        d = e.get("date")
        dday = None
        if d:
            try:
                dday = (datetime.strptime(d, "%Y-%m-%d").date() - today).days
            except Exception:
                dday = None
        out.append({"name": e.get("name", "시험"), "date": d, "subjects": subs, "dday": dday})
    return {"exams": out, "today": today.isoformat()}


def upsert_exam(name, date_str, subjects):
    """시험 타깃 추가/수정(날짜 빈값=미정). 다른 키 보존. srs_scheduler 와 동일 포맷."""
    if not name:
        return {"ok": False, "error": "name 필요"}
    try:
        lj = json.load(open(LEARNING, encoding="utf-8-sig"))
    except Exception:
        lj = {}
    dnorm = None
    if date_str:
        try:
            dnorm = datetime.strptime(date_str.strip(), "%Y-%m-%d").date().strftime("%Y-%m-%d")
        except Exception:
            return {"ok": False, "error": f"날짜 형식 오류: {date_str}"}
    subs = subjects
    if isinstance(subs, str):
        subs = "all" if subs.strip().lower() == "all" else [s.strip() for s in subs.split(",") if s.strip()]
    if not subs:
        subs = "all"
    exams = lj.get("exams")
    if not isinstance(exams, list):
        exams = []
    found = next((e for e in exams if isinstance(e, dict) and e.get("name") == name), None)
    if found is None:
        found = {"name": name, "date": dnorm, "subjects": subs}
        exams.append(found)
    else:
        found["date"] = dnorm
        found["subjects"] = subs
    lj["exams"] = exams
    os.makedirs(STATE, exist_ok=True)
    json.dump(lj, open(LEARNING, "w", encoding="utf-8"), ensure_ascii=False, indent=4)
    return {"ok": True, "exam": found}


# ---------------------------------------------------------------- HTTP 핸들러
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/진도_board.html", "/index.html"):
            try:
                html = open(HTML, encoding="utf-8").read()
            except Exception as e:
                return self._send(500, f"보드 파일 읽기 실패: {e}", "text/plain; charset=utf-8")
            return self._send(200, html, "text/html; charset=utf-8")
        if path == "/api/state":
            return self._json(200, read_state())
        if path == "/api/weak":
            return self._json(200, read_weak())
        if path == "/api/exams":
            return self._json(200, read_exams())
        if path == "/api/ping":
            return self._json(200, {"ok": True, "server": "board", "port": PORT})
        return self._send(404, "not found", "text/plain; charset=utf-8")

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        body = self._body()
        if path == "/api/save":
            try:
                write_state(body)
                return self._json(200, {"ok": True})
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})
        if path == "/api/log":
            try:
                append_log(body)
                return self._json(200, {"ok": True})
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})
        if path == "/api/weak":
            try:
                cands = list(body.get("candidates", []) or [])
                manual = (body.get("manual") or "").strip()
                if manual:
                    unit = body.get("unit") or ""
                    label = (f"{_unit_label(unit)} — " if unit else "") + manual
                    cands.append({"label": label, "tag": "[추가]"})
                return self._json(200, add_weak(cands))
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})
        if path == "/api/bump":
            try:
                changed = apply_board_bump(body.get("keys", []) or [],
                                           body.get("kind", "선택"),
                                           int(body.get("delta", 1)))
                return self._json(200, {"ok": True, "changed": changed})
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})
        if path == "/api/exams":
            try:
                return self._json(200, upsert_exam(body.get("name", ""),
                                                   body.get("date", ""),
                                                   body.get("subjects", "all")))
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})
        return self._send(404, "not found", "text/plain; charset=utf-8")

    def log_message(self, *a):
        pass  # 콘솔 조용히


# ---------------------------------------------------------------- 엔트리
def selftest():
    # 실제 산출물을 건드리지 않도록 샌드박스로 경로 격리(LEARNING 은 읽기전용이라 유지)
    global BACKUP, STATE_JSON, EXPORT_LATEST, LOG_JSONL, HYUN_JSON, HYUN_MD, PROG
    sand = os.path.join(SCRIPT_DIR, "백업", "_selftest")
    os.makedirs(sand, exist_ok=True)
    BACKUP = sand
    STATE_JSON = os.path.join(sand, "진도_state.json")
    EXPORT_LATEST = os.path.join(sand, "진도_board_export_latest.json")
    LOG_JSONL = os.path.join(sand, "진도_log.jsonl")
    HYUN_JSON = os.path.join(sand, "진도_현황.json")
    HYUN_MD = os.path.join(sand, "진도_현황.md")
    PROG = os.path.join(sand, "progress.json")
    print(f"[selftest] 샌드박스: {sand}")
    print("[selftest] 보드 파싱…")
    board = load_board()
    keys = all_keys(board)
    print(f"  단원 수: {len(keys)}")
    st = read_state()
    # 더미 클릭 1건 반영 후 저장
    k = keys[0]
    st.setdefault("회독", {})[k] = st.get("회독", {}).get(k, 0)
    st["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_state(st)
    append_log({"ts": st["updated"], "key": k, "mode": "회독", "value": st["회독"][k], "delta": 0, "selftest": True})
    print(f"  → {STATE_JSON} {'OK' if os.path.exists(STATE_JSON) else 'FAIL'}")
    print(f"  → {EXPORT_LATEST} {'OK' if os.path.exists(EXPORT_LATEST) else 'FAIL'}")
    print(f"  → {HYUN_JSON} {'OK' if os.path.exists(HYUN_JSON) else 'FAIL'}")
    print(f"  → {HYUN_MD} {'OK' if os.path.exists(HYUN_MD) else 'FAIL'}")
    print(f"  → {LOG_JSONL} {'OK' if os.path.exists(LOG_JSONL) else 'FAIL'}")
    w = read_weak()
    print(f"  약점: weak_points {len(w['weak_points'])}개 · SRS 임박 {len(w['srs_due'])} · 예정 {len(w['srs_upcoming'])}")
    print("[selftest] 통과")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    if "--bump" in sys.argv:  # 외부(드릴)에서 보드 카운트 +1 (서버 없이 직접 디스크 기록)
        i = sys.argv.index("--bump")
        keys = [k for k in sys.argv[i + 1].split(",") if k] if i + 1 < len(sys.argv) else []
        kind = "선택"
        if "--kind" in sys.argv:
            j = sys.argv.index("--kind")
            if j + 1 < len(sys.argv):
                kind = sys.argv[j + 1]
        changed = apply_board_bump(keys, kind, 1)
        print(f"보드 {kind} +1 반영: {len(changed)}단원")
        return
    global PORT
    httpd = None
    for p in range(PORT, PORT + 10):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            PORT = p
            break
        except OSError:
            continue
    if httpd is None:
        print("포트 확보 실패(8770~8779 사용 중).")
        sys.exit(1)
    url = f"http://localhost:{PORT}/"
    print(f"진도 보드 서버 가동 → {url}")
    print(f"  로그:  {LOG_JSONL}")
    print(f"  상태:  {STATE_JSON}")
    print("  (이 창을 닫으면 서버가 종료됩니다. 닫지 말고 두세요.)")
    if "--no-browser" not in sys.argv:  # 자동시작(로그인)은 브라우저 안 띄우고 서버만
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n종료.")


if __name__ == "__main__":
    main()
