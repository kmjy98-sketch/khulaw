#!/usr/bin/env python3
"""Progress Tracker: 학습 진도 (수동입력·목차단원판, 2026-06-18).
스키마: 과목 > 단원(大단원) > {상태,회독,세부[]}. 전사문 자동추적 폐기.
조회(--status) / 단원 갱신(--set 과목 --unit 단원 ...) / 로드맵(--goal). 직접 편집도 가능."""
import argparse, json, sys
from datetime import date
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

PATH = Path(__file__).parent.parent.parent.parent / "state" / "progress.json"
STATES = ("예정", "진행중", "종료")


def load():
    if PATH.exists():
        with open(PATH, encoding="utf-8-sig") as f:
            return json.load(f)
    return {"로드맵": {}, "과목": {}}


def save(d):
    d["최종수정"] = str(date.today())
    PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=4)


def show(d):
    rm = d.get("로드맵", {})
    print(f"[학습 진도 — 수동입력]  최종수정: {d.get('최종수정', 'N/A')}")
    print(f"  [로드맵] 전체:{rm.get('전체목표', '-')} / 방학:{rm.get('이번방학목표', '-')} / 학기:{rm.get('다음학기목표', '-')}")
    for subj, units in d.get("과목", {}).items():
        if not isinstance(units, dict):
            continue
        done = sum(1 for u in units.values() if isinstance(u, dict) and u.get("상태") == "종료")
        print(f"  [{subj}]  ({done}/{len(units)} 종료)")
        for name, s in units.items():
            st = (s.get("상태") or "-") if isinstance(s, dict) else "-"
            rd = s.get("회독") if isinstance(s, dict) else None
            rd = f"{rd}회독" if isinstance(rd, int) else "-"
            print(f"    {name:<14} {st:<5} {rd}")


def set_unit(d, subj, unit, args):
    units = d.setdefault("과목", {}).setdefault(subj, {})
    u = units.setdefault(unit, {"상태": "", "회독": None, "세부": []})
    if args.state:
        if args.state not in STATES:
            print(f"상태는 {STATES} 중 하나"); return False
        u["상태"] = args.state
    if args.rounds is not None:
        u["회독"] = args.rounds
    if args.memo is not None:
        u["메모"] = args.memo
    if args.done:
        u["상태"] = "종료"
    print(f"갱신: {subj} > {unit} = 상태 {u.get('상태') or '-'} / 회독 {u.get('회독')}")
    return True


def main():
    p = argparse.ArgumentParser(description="학습 진도(수동입력·목차단원)")
    p.add_argument("--status", "-s", action="store_true", help="진도 조회")
    p.add_argument("--set", dest="subject", help="과목명(예: 민법)")
    p.add_argument("--unit", help="단원명(예: 물권법). --set과 함께")
    p.add_argument("--state", help=f"상태 {STATES}")
    p.add_argument("--rounds", type=int, help="회독 수")
    p.add_argument("--memo", help="메모")
    p.add_argument("--done", action="store_true", help="종료 처리")
    p.add_argument("--goal", nargs=2, metavar=("KIND", "TEXT"), help="로드맵 KIND=전체|방학|학기")
    args = p.parse_args()

    if not (args.status or args.subject or args.goal):
        p.print_help(); sys.exit(1)
    d = load()
    if args.goal:
        key = {"전체": "전체목표", "방학": "이번방학목표", "학기": "다음학기목표"}.get(args.goal[0])
        if not key:
            print("KIND는 전체|방학|학기"); sys.exit(1)
        d.setdefault("로드맵", {})[key] = args.goal[1]; save(d); print(f"목표 갱신: {key}={args.goal[1]}")
    elif args.subject:
        if not args.unit:
            print("단원을 지정하세요: --set 과목 --unit 단원"); sys.exit(1)
        if set_unit(d, args.subject, args.unit, args):
            save(d)
    if args.status:
        show(d)


if __name__ == "__main__":
    main()
