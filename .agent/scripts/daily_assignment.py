#!/usr/bin/env python3
# 목표 기반 아침/저녁 학습 루틴 보조 스크립트 (multi-active 지원).
#
# 핵심 컨셉:
#   - 사용자가 목표(예: 기말고사·국제법·법조윤리)를 여러 개 동시에 활성화 가능.
#   - 각 목표의 deadline·buffer_days·targets에서 일별 quota 자동 산정.
#   - 진도 땡겨오기 (advance_balance): quota 초과분 → 다음 며칠 quota 0(휴식일).
#   - deadline - buffer_days 도달 시 review 모드 자동 전환 (새 진도 X, 약점·SRS 위주).
#   - 인지과학: Interleaving (과목 + 목표 섞기), Spaced Repetition,
#     Retrieval Practice, Desirable Difficulty.
#
# Subcommands:
#   morning  - 모든 active goal에서 quota 산정 + 인터리빙 후보
#   evening  - 결과 → 각 goal.progress 누적, 보너스 → advance_balance
#   record   - 풀이 결과 기록 (cand.goal_id 자동 매핑)
#   goal     - show / set / activate / deactivate / add-extra / mode
#   status   - 오늘 진행 현황
#
# state:
#   .agent/state/{progress, learning, srs_log, problem_index, goals, daily_log}.json

import argparse
import json
import math
import sys
from datetime import datetime, date, timedelta
from itertools import zip_longest
from pathlib import Path

# Windows 콘솔 cp949 mojibake 방지
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".agent" / "state"

PROGRESS = STATE / "progress.json"
LEARNING = STATE / "learning.json"
SRS = STATE / "srs_log.json"
PROBLEM_INDEX = STATE / "problem_index.json"
GOALS = STATE / "goals.json"
DAILY_LOG = STATE / "daily_log.json"


# ---- IO ----

def load_json(path, default=None):
    if not path.exists():
        return default if default is not None else {}
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def today_iso():
    return date.today().isoformat()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def parse_iso(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


# ---- Subject normalize ----

_SUBJECT_PREFIXES = ("민법", "형법", "헌법", "민소", "형소", "행정", "선택", "국제", "법조")


def _normalize_subject(s):
    if not s:
        return None
    for p in _SUBJECT_PREFIXES:
        if s.startswith(p):
            return p
    return s


# ---- Goals (multi-active) ----

def load_goals():
    return load_json(GOALS, default={"active": [], "goals": {}})


def _active_list(goals):
    a = goals.get("active")
    if a is None:
        return []
    if isinstance(a, str):
        return [a] if a else []
    if isinstance(a, list):
        return [x for x in a if x]
    return []


def get_active_goals(goals):
    out = []
    for aid in _active_list(goals):
        g = goals.get("goals", {}).get(aid)
        if g:
            out.append((aid, g))
    return out


def get_active_goal(goals):
    items = get_active_goals(goals)
    return items[0] if items else (None, None)


def determine_mode(goal, today):
    if not goal:
        return "normal", None
    if goal.get("force_mode") in ("normal", "review"):
        deadline = parse_iso(goal.get("deadline"))
        buffer_days = int(goal.get("buffer_days") or 0)
        rs = (deadline - timedelta(days=buffer_days)).isoformat() if deadline else None
        return goal["force_mode"], rs
    deadline = parse_iso(goal.get("deadline"))
    buffer_days = int(goal.get("buffer_days") or 0)
    if not deadline:
        return "normal", None
    review_start = deadline - timedelta(days=buffer_days)
    if parse_iso(today) >= review_start:
        return "review", review_start.isoformat()
    return "normal", review_start.isoformat()


def compute_quota(goal, today, consume_advance=False):
    out = {}
    if not goal:
        return out
    deadline = parse_iso(goal.get("deadline"))
    buffer_days = int(goal.get("buffer_days") or 0)
    targets = goal.get("targets", {})
    progress = goal.get("progress", {})
    advance = goal.setdefault("advance_balance", {})
    today_d = parse_iso(today)
    if deadline:
        review_start = deadline - timedelta(days=buffer_days)
        days_left = max(1, (review_start - today_d).days)
    else:
        days_left = 7
    case_window = max(1, days_left // 2)
    for subj, tgt in targets.items():
        prog = progress.get(subj, {})
        ox_remaining = max(0, int(tgt.get("ox", 0)) - int(prog.get("ox_done", 0)))
        case_remaining = max(0, int(tgt.get("case", 0)) - int(prog.get("case_done", 0)))
        base_ox = math.ceil(ox_remaining / days_left) if ox_remaining else 0
        base_case = math.ceil(case_remaining / case_window) if case_remaining else 0
        adv_node = advance.setdefault(subj, {"ox": 0, "case": 0})
        adv_ox = int(adv_node.get("ox", 0))
        adv_case = int(adv_node.get("case", 0))
        today_ox = max(0, base_ox - adv_ox)
        today_case = max(0, base_case - adv_case)
        out[subj] = {
            "ox": today_ox,
            "case": today_case,
            "remaining_ox": ox_remaining,
            "remaining_case": case_remaining,
            "base_ox": base_ox,
            "base_case": base_case,
            "advance_ox": adv_ox,
            "advance_case": adv_case,
            "advance_ox_used": min(base_ox, adv_ox),
            "advance_case_used": min(base_case, adv_case),
            "rest_day": (today_ox == 0 and base_ox > 0),
            "days_left_to_review": days_left,
        }
        if consume_advance:
            adv_node["ox"] = max(0, adv_ox - base_ox)
            adv_node["case"] = max(0, adv_case - base_case)
    return out


def remaining_summary(goal):
    if not goal:
        return {}
    out = {}
    targets = goal.get("targets", {})
    progress = goal.get("progress", {})
    for subj, tgt in targets.items():
        prog = progress.get(subj, {})
        ox_done = int(prog.get("ox_done", 0))
        ox_total = int(tgt.get("ox", 0))
        case_done = int(prog.get("case_done", 0))
        case_total = int(tgt.get("case", 0))
        out[subj] = {
            "ox": "{}/{}".format(ox_done, ox_total),
            "case": "{}/{}".format(case_done, case_total),
            "ox_pct": round(100 * ox_done / ox_total, 1) if ox_total else 0.0,
        }
    return out


def estimate_buffer_arrival(goal, today):
    if not goal:
        return None
    deadline = parse_iso(goal.get("deadline"))
    buffer_days = int(goal.get("buffer_days") or 0)
    if not deadline:
        return None
    targets = goal.get("targets", {})
    progress = goal.get("progress", {})
    created = parse_iso(goal.get("created")) or parse_iso(today)
    today_d = parse_iso(today)
    days_elapsed = max(1, (today_d - created).days)
    total_done = sum(int(progress.get(s, {}).get("ox_done", 0)) for s in targets)
    total_target = sum(int(targets[s].get("ox", 0)) for s in targets)
    if total_done == 0:
        return {
            "projected_completion": None,
            "review_start": (deadline - timedelta(days=buffer_days)).isoformat(),
            "days_left_to_deadline": (deadline - today_d).days,
        }
    pace = total_done / days_elapsed
    remaining_total = max(0, total_target - total_done)
    days_to_finish = math.ceil(remaining_total / pace) if pace > 0 else None
    projected = today_d + timedelta(days=days_to_finish) if days_to_finish is not None else None
    return {
        "projected_completion": projected.isoformat() if projected else None,
        "review_start": (deadline - timedelta(days=buffer_days)).isoformat(),
        "pace_ox_per_day": round(pace, 2),
        "days_left_to_deadline": (deadline - today_d).days,
    }


# ---- Problem candidates ----

def get_srs_due(srs_log, today):
    items = srs_log.get("items", []) if isinstance(srs_log, dict) else []
    return [
        {
            "id": it.get("id"),
            "content": it.get("content"),
            "topic": it.get("topic"),
            "next_review": it.get("next_review"),
            "priority": it.get("priority", "medium"),
        }
        for it in items
        if str(it.get("next_review", "9999-12-31")) <= today
    ]


def get_weak_points(learning):
    return learning.get("weak_points", [])


def pick_subject_ox(problem_index, subj_norm, count):
    if not problem_index or not subj_norm or count <= 0:
        return []
    node = problem_index.get("subjects", {}).get(subj_norm)
    if not node:
        return []
    topics = node.get("topics", {}) or {}
    verified, unverified = [], []
    for topic_name, topic_data in topics.items():
        dts = (topic_data.get("problems", {}) or {}).get("dt", []) or []
        for idx, dt in enumerate(dts):
            if not isinstance(dt, dict):
                continue
            rec = {
                "subject": subj_norm,
                "topic": topic_name,
                "topic_path": topic_data.get("toc_path"),
                "index": idx,
                "file": dt.get("file"),
                "answer": dt.get("answer"),
                "verified": bool(dt.get("verified")),
                "display_label": dt.get("display_label"),
            }
            (verified if rec["verified"] else unverified).append(rec)
    picked = verified[:count]
    if len(picked) < count:
        picked += unverified[: count - len(picked)]
    return picked


def interleave(per_subject_lists):
    out = []
    if not per_subject_lists:
        return out
    for chunk in zip_longest(*per_subject_lists, fillvalue=None):
        for item in chunk:
            if item is not None:
                out.append(item)
    return out


# ---- Daily log ----

def load_daily_log():
    return load_json(DAILY_LOG, default={"logs": {}})


def save_daily(today, key, payload):
    log = load_daily_log()
    log.setdefault("logs", {}).setdefault(today, {})[key] = payload
    save_json(DAILY_LOG, log)


def yesterday_log():
    log = load_daily_log()
    yest = (date.today() - timedelta(days=1)).isoformat()
    return log.get("logs", {}).get(yest, {})


# ---- Commands: morning ----

def _parse_goal_spec(spec):
    # "민법1:10,형법1:5" → {"민법1": 10, ...}
    out = {}
    if not spec:
        return out
    for kv in spec.split(","):
        if ":" in kv:
            k, v = kv.split(":", 1)
            try:
                out[k.strip()] = int(v.strip())
            except ValueError:
                pass
    return out


def cmd_morning(args):
    progress = load_json(PROGRESS)
    learning = load_json(LEARNING)
    srs = load_json(SRS)
    pi = load_json(PROBLEM_INDEX)
    goals = load_goals()
    today = today_iso()

    actives = get_active_goals(goals)
    if not actives:
        print(json.dumps({"error": "활성 목표가 없습니다. 'goal set --activate' 또는 'goal activate --id <gid>'로 활성화하세요."},
                         ensure_ascii=False, indent=2))
        return 1

    log_now = load_daily_log()
    already_today = bool(log_now.get("logs", {}).get(today, {}).get("morning"))
    spec_override = _parse_goal_spec(args.goal_spec)

    goal_payloads = []
    per_goal_candidates = []   # 각 goal의 인터리빙된 후보 리스트

    for goal_id, goal in actives:
        mode, review_start = determine_mode(goal, today)
        quota = compute_quota(goal, today, consume_advance=not already_today)

        per_subject = []
        for subj in goal.get("subjects", []):
            sn = _normalize_subject(subj)
            if mode == "review":
                n = spec_override.get(subj, 5)
            else:
                n = spec_override.get(subj, quota.get(subj, {}).get("ox", 5))
            cands = pick_subject_ox(pi, sn, max(0, n))
            for c in cands:
                c["goal_id"] = goal_id
                c["goal_title"] = goal.get("title")
                c["subject_full"] = subj
            per_subject.append(cands)

        if goal.get("cognitive_strategies", {}).get("interleaving", True):
            interleaved_for_goal = interleave(per_subject)
        else:
            interleaved_for_goal = [it for chunk in per_subject for it in chunk]
        per_goal_candidates.append(interleaved_for_goal)

        goal_payloads.append({
            "goal_id": goal_id,
            "title": goal.get("title"),
            "deadline": goal.get("deadline"),
            "buffer_days": goal.get("buffer_days"),
            "review_start": review_start,
            "mode": mode,
            "quota": quota,
            "remaining": remaining_summary(goal),
            "buffer_estimate": estimate_buffer_arrival(goal, today),
            "syllabus_refs": goal.get("syllabus_refs", []),
            "scope_by_subject": goal.get("scope_by_subject", {}),
        })

    if not already_today:
        save_json(GOALS, goals)

    # 목표끼리도 인터리빙 (round-robin)
    final_candidates = interleave(per_goal_candidates)

    yest = yesterday_log()
    ask_extra = bool(yest.get("evening")) and not yest.get("extra_logged_today")

    payload = {
        "generated_at": now_iso(),
        "today": today,
        "active_goals": goal_payloads,
        "ox_candidates": final_candidates,
        "srs_due": get_srs_due(srs, today),
        "weak_points": get_weak_points(learning),
        "case_seed": {
            "current_topic": learning.get("current_scope"),
            "scope_textbook": progress.get("current_scope", {}).get("textbook"),
            "page_range": progress.get("current_scope", {}).get("page_range"),
            "primary_weak_point": (get_weak_points(learning) or [None])[0],
        },
        "ask_extra_yesterday": ask_extra,
        "results": {"ox": [], "case": [], "srs": []},
    }
    save_daily(today, "morning", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


# ---- Commands: evening ----

def cmd_evening(args):
    log = load_daily_log()
    today = today_iso()
    today_log = log.get("logs", {}).get(today, {})
    morning = today_log.get("morning")
    if not morning:
        print(json.dumps({"error": "오늘 아침 숙제가 없습니다.", "today": today}, ensure_ascii=False, indent=2))
        return 1

    results = morning.get("results", {})
    ox_results = results.get("ox", [])
    case_results = results.get("case", [])
    srs_results = results.get("srs", [])

    ox_total = len(ox_results)
    ox_correct = sum(1 for r in ox_results if r.get("correct") is True)
    ox_wrong = [r for r in ox_results if r.get("correct") is False]

    goals = load_goals()
    actives = get_active_goals(goals)

    # goal_id → {subject_full → {ox: int, case: int}}
    done_by_goal = {}
    for r in ox_results:
        if r.get("correct") is True:
            gid = r.get("goal_id")
            subj = r.get("subject_full") or r.get("subject")
            if gid:
                node = done_by_goal.setdefault(gid, {}).setdefault(subj, {"ox": 0, "case": 0})
                node["ox"] += 1
    for c in case_results:
        if c.get("done"):
            gid = c.get("goal_id")
            subj = c.get("subject_full") or c.get("subject")
            if gid:
                node = done_by_goal.setdefault(gid, {}).setdefault(subj, {"ox": 0, "case": 0})
                node["case"] += 1

    bonus_by_goal = []
    remaining_by_goal = []

    morning_active = morning.get("active_goals", [])
    morning_quota_map = {g.get("goal_id"): g.get("quota", {}) for g in morning_active}

    for goal_id, goal in actives:
        # extra_study_log 오늘분 합산
        for entry in goal.get("extra_study_log", []):
            if entry.get("date") == today:
                subj = entry.get("subject")
                if subj and subj in goal.get("targets", {}):
                    node = done_by_goal.setdefault(goal_id, {}).setdefault(subj, {"ox": 0, "case": 0})
                    node["ox"] += int(entry.get("ox", 0) or 0)
                    node["case"] += int(entry.get("case", 0) or 0)

        # progress 누적
        gd = done_by_goal.get(goal_id, {})
        for subj, counts in gd.items():
            if subj not in goal.get("targets", {}):
                continue
            pnode = goal["progress"].setdefault(subj, {"ox_done": 0, "case_done": 0})
            pnode["ox_done"] = int(pnode.get("ox_done", 0)) + int(counts.get("ox", 0))
            pnode["case_done"] = int(pnode.get("case_done", 0)) + int(counts.get("case", 0))

        # 보너스 → advance_balance
        quota_today = morning_quota_map.get(goal_id, {})
        adv_root = goal.setdefault("advance_balance", {})
        g_bonus = []
        for subj in goal.get("targets", {}):
            ox_q = int(quota_today.get(subj, {}).get("ox", 0))
            case_q = int(quota_today.get(subj, {}).get("case", 0))
            ox_d = gd.get(subj, {}).get("ox", 0)
            case_d = gd.get(subj, {}).get("case", 0)
            ox_extra = max(0, ox_d - ox_q)
            case_extra = max(0, case_d - case_q)
            if ox_extra or case_extra:
                node = adv_root.setdefault(subj, {"ox": 0, "case": 0})
                node["ox"] = int(node.get("ox", 0)) + ox_extra
                node["case"] = int(node.get("case", 0)) + case_extra
                g_bonus.append({
                    "subject": subj,
                    "ox_extra": ox_extra,
                    "case_extra": case_extra,
                    "advance_balance_after": dict(node),
                })
        if g_bonus:
            bonus_by_goal.append({"goal_id": goal_id, "title": goal.get("title"), "items": g_bonus})

        remaining_by_goal.append({
            "goal_id": goal_id,
            "title": goal.get("title"),
            "remaining": remaining_summary(goal),
            "buffer_estimate": estimate_buffer_arrival(goal, today),
        })

    save_json(GOALS, goals)
    today_log["extra_logged_today"] = True
    log.setdefault("logs", {})[today] = today_log
    save_json(DAILY_LOG, log)

    payload = {
        "completed_at": now_iso(),
        "today": today,
        "ox_score": "{}/{}".format(ox_correct, ox_total) if ox_total else "0/0",
        "ox_pct": round(100 * ox_correct / ox_total, 1) if ox_total else 0.0,
        "ox_wrong": [
            {
                "goal_id": r.get("goal_id"),
                "subject": r.get("subject_full") or r.get("subject"),
                "topic": r.get("topic"),
                "given": r.get("given"),
                "expected": r.get("expected"),
            }
            for r in ox_wrong
        ],
        "case_done": sum(1 for c in case_results if c.get("done")),
        "srs_reviewed": len(srs_results),
        "bonus_by_goal": bonus_by_goal,
        "remaining_by_goal": remaining_by_goal,
        "tomorrow_hint": "내일 08:00 'morning' 호출 → multi-goal 인터리빙 quota",
    }
    save_daily(today, "evening", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


# ---- Commands: record ----

def cmd_record(args):
    log = load_daily_log()
    today = today_iso()
    today_log = log.get("logs", {}).setdefault(today, {})
    morning = today_log.get("morning")
    if not morning:
        print(json.dumps({"error": "오늘 아침 숙제가 없습니다."}, ensure_ascii=False, indent=2))
        return 1

    results = morning.setdefault("results", {"ox": [], "case": [], "srs": []})

    if args.ox:
        marks = _parse_ox_string(args.ox)
        cands = morning.get("ox_candidates", [])
        offset = len(results.get("ox", []))
        for i, mark in enumerate(marks):
            ci = offset + i
            if ci >= len(cands):
                break
            cand = cands[ci]
            expected = cand.get("answer")
            correct = (mark == expected) if expected in ("O", "X") else None
            results["ox"].append({
                "id": "{}::{}::{}".format(cand.get("subject", "?"), cand.get("topic", "?"), cand.get("index")),
                "goal_id": cand.get("goal_id"),
                "goal_title": cand.get("goal_title"),
                "subject": cand.get("subject"),
                "subject_full": cand.get("subject_full"),
                "topic": cand.get("topic"),
                "given": mark,
                "expected": expected,
                "correct": correct,
            })

    if args.case:
        gid = args.case_goal_id
        if not gid and args.case_subject:
            goals_loaded = load_goals()
            for aid, g in get_active_goals(goals_loaded):
                if args.case_subject in g.get("targets", {}):
                    gid = aid
                    break
        results.setdefault("case", []).append({
            "goal_id": gid,
            "subject_full": args.case_subject,
            "subject": args.case_subject,
            "topic": args.case_topic or "case",
            "done": True,
            "score": args.case,
            "note": args.note,
        })

    if args.srs_score is not None and args.srs_id is not None:
        results.setdefault("srs", []).append({"id": args.srs_id, "score": args.srs_score})

    save_json(DAILY_LOG, log)
    print(json.dumps({"ok": True, "results_count": {
        "ox": len(results.get("ox", [])),
        "case": len(results.get("case", [])),
        "srs": len(results.get("srs", [])),
    }}, ensure_ascii=False, indent=2))
    return 0


# ---- Commands: status ----

def cmd_status(args):
    log = load_daily_log()
    today = today_iso()
    today_log = log.get("logs", {}).get(today, {})
    morning = today_log.get("morning") or {}
    evening = today_log.get("evening")
    cands = morning.get("ox_candidates", [])
    results = morning.get("results", {})
    print(json.dumps({
        "today": today,
        "active_goals": [g.get("goal_id") for g in morning.get("active_goals", [])],
        "morning_set": bool(morning),
        "evening_set": bool(evening),
        "ox_progress": "{}/{}".format(len(results.get("ox", [])), len(cands)),
        "case_progress": len(results.get("case", [])),
        "srs_progress": len(results.get("srs", [])),
        "srs_due_count": len(morning.get("srs_due", [])),
    }, ensure_ascii=False, indent=2))
    return 0


# ---- Commands: goal ----

def _serialize_goal(gid, goal, today):
    mode, review_start = determine_mode(goal, today)
    return {
        "goal_id": gid,
        "title": goal.get("title"),
        "deadline": goal.get("deadline"),
        "buffer_days": goal.get("buffer_days"),
        "review_start": review_start,
        "mode": mode,
        "subjects": goal.get("subjects", []),
        "remaining": remaining_summary(goal),
        "quota_today": compute_quota(goal, today),
        "buffer_estimate": estimate_buffer_arrival(goal, today),
        "syllabus_refs": goal.get("syllabus_refs", []),
        "scope_by_subject": goal.get("scope_by_subject", {}),
    }


def cmd_goal(args):
    goals = load_goals()
    today = today_iso()

    if args.action == "show":
        if args.id:
            goal = goals.get("goals", {}).get(args.id)
            if not goal:
                print(json.dumps({"error": "존재하지 않는 goal_id: " + args.id}, ensure_ascii=False, indent=2))
                return 1
            print(json.dumps({"active": _active_list(goals), "goals": [_serialize_goal(args.id, goal, today)]},
                             ensure_ascii=False, indent=2))
            return 0
        actives = get_active_goals(goals)
        if not actives:
            print(json.dumps({"error": "활성 목표가 없습니다."}, ensure_ascii=False, indent=2))
            return 1
        print(json.dumps({
            "active": _active_list(goals),
            "goals": [_serialize_goal(gid, g, today) for gid, g in actives],
        }, ensure_ascii=False, indent=2))
        return 0

    if args.action == "set":
        gid = args.id or (_active_list(goals) or ["final_exam"])[0]
        node = goals.setdefault("goals", {}).setdefault(gid, {
            "subjects": [], "targets": {}, "progress": {},
            "advance_balance": {},
            "extra_study_log": [], "created": today,
            "cognitive_strategies": {
                "spaced_repetition": True, "interleaving": True,
                "retrieval_practice": True, "elaboration": True,
                "dual_coding": False, "desirable_difficulty": True,
            },
            "schedule": {"morning": "08:00", "evening": "22:00"},
            "syllabus_refs": [], "scope_by_subject": {},
        })
        if args.title:
            node["title"] = args.title
        if args.deadline:
            node["deadline"] = args.deadline
        if args.buffer_days is not None:
            node["buffer_days"] = args.buffer_days
        if args.subjects:
            node["subjects"] = [s.strip() for s in args.subjects.split(",") if s.strip()]
        if args.targets:
            for kv in args.targets.split(","):
                if ":" not in kv:
                    continue
                subj, spec = kv.split(":", 1)
                subj = subj.strip()
                tgt = node["targets"].setdefault(subj, {"ox": 0, "case": 0})
                for piece in spec.split("+"):
                    piece = piece.strip()
                    if piece.startswith("ox"):
                        tgt["ox"] = int(piece[2:])
                    elif piece.startswith("case"):
                        tgt["case"] = int(piece[4:])
                node["progress"].setdefault(subj, {"ox_done": 0, "case_done": 0})
                node["advance_balance"].setdefault(subj, {"ox": 0, "case": 0})
        if args.syllabus:
            for p in args.syllabus.split(","):
                p = p.strip()
                if p and p not in node.setdefault("syllabus_refs", []):
                    node["syllabus_refs"].append(p)
        if args.scope:
            # 형식: "민법1=권리주체~의사표시;형법1=총론서론~위법성"
            scope_map = node.setdefault("scope_by_subject", {})
            for chunk in args.scope.split(";"):
                if "=" in chunk:
                    sk, sv = chunk.split("=", 1)
                    scope_map[sk.strip()] = sv.strip()
        if args.activate:
            current = _active_list(goals)
            if gid not in current:
                current.append(gid)
            goals["active"] = current
        save_json(GOALS, goals)
        print(json.dumps({"ok": True, "goal_id": gid, "active": _active_list(goals), "goal": node},
                         ensure_ascii=False, indent=2))
        return 0

    if args.action == "activate":
        if not args.id:
            print(json.dumps({"error": "--id 필요"}, ensure_ascii=False, indent=2))
            return 1
        if args.id not in goals.get("goals", {}):
            print(json.dumps({"error": "존재하지 않는 goal_id: " + args.id}, ensure_ascii=False, indent=2))
            return 1
        current = _active_list(goals)
        if args.replace:
            current = [args.id]
        elif args.id not in current:
            current.append(args.id)
        goals["active"] = current
        save_json(GOALS, goals)
        print(json.dumps({"ok": True, "active": current}, ensure_ascii=False, indent=2))
        return 0

    if args.action == "deactivate":
        if not args.id:
            print(json.dumps({"error": "--id 필요"}, ensure_ascii=False, indent=2))
            return 1
        current = _active_list(goals)
        if args.id in current:
            current.remove(args.id)
        goals["active"] = current
        save_json(GOALS, goals)
        print(json.dumps({"ok": True, "active": current}, ensure_ascii=False, indent=2))
        return 0

    if args.action == "add-extra":
        gid = args.goal_id
        if not gid:
            for aid, g in get_active_goals(goals):
                if args.subject in g.get("targets", {}):
                    gid = aid
                    break
        if not gid:
            actives = get_active_goals(goals)
            if not actives:
                print(json.dumps({"error": "활성 목표가 없습니다."}, ensure_ascii=False, indent=2))
                return 1
            gid = actives[0][0]
        goal = goals.get("goals", {}).get(gid)
        if not goal:
            print(json.dumps({"error": "goal not found: " + gid}, ensure_ascii=False, indent=2))
            return 1
        entry = {
            "date": args.date or today,
            "subject": args.subject,
            "ox": args.ox or 0,
            "case": args.case or 0,
            "note": args.note,
            "logged_at": now_iso(),
        }
        goal.setdefault("extra_study_log", []).append(entry)
        save_json(GOALS, goals)
        print(json.dumps({"ok": True, "goal_id": gid, "entry": entry}, ensure_ascii=False, indent=2))
        return 0

    if args.action == "mode":
        if args.force not in ("normal", "review", "auto"):
            print(json.dumps({"error": "--force normal|review|auto"}, ensure_ascii=False, indent=2))
            return 1
        target_ids = [args.id] if args.id else [aid for aid, _ in get_active_goals(goals)]
        if not target_ids:
            print(json.dumps({"error": "대상 goal 없음"}, ensure_ascii=False, indent=2))
            return 1
        for gid in target_ids:
            goal = goals.get("goals", {}).get(gid)
            if not goal:
                continue
            if args.force == "auto":
                goal.pop("force_mode", None)
            else:
                goal["force_mode"] = args.force
        save_json(GOALS, goals)
        print(json.dumps({"ok": True, "force": args.force, "goals": target_ids}, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps({"error": "알 수 없는 goal action"}, ensure_ascii=False, indent=2))
    return 1


# ---- 내부 유틸 ----

_OX_MAP = {
    "O": "O", "o": "O", "1": "O", "ㅇ": "O",
    "X": "X", "x": "X", "2": "X", "ㅌ": "X",
    "?": "?", "ㅁ": "?", "3": "?",
}


def _parse_ox_string(s):
    cleaned = "".join(ch for ch in s if not ch.isspace() and ch != ",")
    return [_OX_MAP.get(ch, "?") for ch in cleaned]


# ---- main ----

def main():
    p = argparse.ArgumentParser(description="목표 기반 아침/저녁 학습 루틴 보조 도구 (multi-active)")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("morning", help="모든 active goal에서 오늘 숙제 생성")
    m.add_argument("--goal-spec", help="과목별 즉시 quota override, 예: '민법1:10,형법1:5'")
    m.set_defaults(func=cmd_morning)

    e = sub.add_parser("evening", help="저녁 점검 + 모든 active goal progress 누적")
    e.set_defaults(func=cmd_evening)

    r = sub.add_parser("record", help="채점 결과 입력")
    r.add_argument("--ox", help="OX 결과 문자열, 예: OXOOX")
    r.add_argument("--case", help="사례 점수, 예: 4/5")
    r.add_argument("--case-topic", help="사례 토픽")
    r.add_argument("--case-subject", help="사례 과목 (예: 민법1)")
    r.add_argument("--case-goal-id", help="사례 goal_id (생략 시 subject로 자동 매칭)")
    r.add_argument("--note", help="메모")
    r.add_argument("--srs-id", type=int, help="SRS 항목 id")
    r.add_argument("--srs-score", type=int, help="SRS 점수 0-5")
    r.set_defaults(func=cmd_record)

    s = sub.add_parser("status", help="오늘 진행 현황")
    s.set_defaults(func=cmd_status)

    g = sub.add_parser("goal", help="show / set / activate / deactivate / add-extra / mode")
    g.add_argument("action", choices=["show", "set", "activate", "deactivate", "add-extra", "mode"])
    g.add_argument("--id", help="goal_id (예: final_exam, intl_law, legal_ethics)")
    g.add_argument("--title")
    g.add_argument("--deadline", help="YYYY-MM-DD")
    g.add_argument("--buffer-days", type=int)
    g.add_argument("--subjects", help="콤마 구분, 예: 민법1,민법3,형법1,헌법1")
    g.add_argument("--targets", help="과목:사양 콤마 구분, 예: '민법1:ox40+case5'")
    g.add_argument("--syllabus", help="수업계획서 파일 경로 콤마 구분, syllabus_refs에 추가")
    g.add_argument("--scope", help="과목별 진도 범위, 예: '민법1=권리주체~의사표시;형법1=총론서론~위법성'")
    g.add_argument("--activate", action="store_true", help="set 후 active list에 추가")
    g.add_argument("--replace", action="store_true", help="activate 시 list 통째 교체")
    g.add_argument("--goal-id", help="add-extra 시 goal_id 명시")
    g.add_argument("--subject", help="add-extra 시 과목")
    g.add_argument("--ox", type=int, help="add-extra OX 수")
    g.add_argument("--case", type=int, help="add-extra 사례 수")
    g.add_argument("--date", help="add-extra 일자 (기본 today)")
    g.add_argument("--note")
    g.add_argument("--force", choices=["normal", "review", "auto"], help="mode 강제")
    g.set_defaults(func=cmd_goal)

    args = p.parse_args()
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
