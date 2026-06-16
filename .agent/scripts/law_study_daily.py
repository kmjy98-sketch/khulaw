#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate daily law-study dashboard files from the SQLite ledger."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / ".agent" / "state" / "progress.sqlite"
STATE_DIR = ROOT / ".agent" / "state"
PENDING_THRESHOLD = 50


def query_all(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    return list(conn.execute(sql, params))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def category_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return query_all(
        conn,
        """
        SELECT
          c.category_id,
          c.subject_group,
          c.subject,
          c.anki_deck,
          COUNT(DISTINCT i.issue_id) AS issue_count,
          COUNT(DISTINCT CASE WHEN i.status IN ('done', 'completed', 'reviewed') THEN i.issue_id END) AS done_issues,
          COUNT(DISTINCT p.problem_id) AS problem_count,
          COUNT(DISTINCT CASE WHEN p.status IN ('done', 'completed', 'reviewed') THEN p.problem_id END) AS done_problems,
          COUNT(DISTINCT w.issue_id) AS weak_count,
          COUNT(DISTINCT a.card_id) AS pending_cards
        FROM categories c
        LEFT JOIN issues i ON i.category_id = c.category_id
        LEFT JOIN problems p ON p.category_id = c.category_id
        LEFT JOIN weak_points w ON w.category_id = c.category_id AND COALESCE(w.severity, 0) > 0
        LEFT JOIN anki_candidates a ON a.category_id = c.category_id AND a.status IN ('pending', 'updated')
        WHERE c.status = 'active'
        GROUP BY c.category_id
        ORDER BY c.subject_group, c.subject, c.category_id
        """,
    )


def overdue_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return query_all(
        conn,
        """
        SELECT queue_id, issue_id, problem_id, category_id, due_date, review_type, reason, priority
        FROM review_queue
        WHERE status = 'scheduled' AND due_date <= ?
        ORDER BY priority DESC, due_date ASC
        LIMIT 20
        """,
        (date.today().isoformat(),),
    )


def weak_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return query_all(
        conn,
        """
        SELECT issue_id, category_id, topic, error_count, repeat_error_count,
               main_weakness, next_action, severity, updated_at
        FROM weak_points
        WHERE COALESCE(severity, 0) > 0
        ORDER BY severity DESC, repeat_error_count DESC, error_count DESC
        LIMIT 30
        """,
    )


def anki_notice_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return query_all(
        conn,
        """
        SELECT c.category_id, c.subject_group, c.anki_deck,
               COUNT(a.card_id) AS pending_cards,
               MAX(b.generated_at) AS last_batch_at
        FROM categories c
        LEFT JOIN anki_candidates a
          ON a.category_id = c.category_id AND a.status IN ('pending', 'updated')
        LEFT JOIN anki_batches b
          ON b.category_id = c.category_id AND b.status IN ('generated', 'imported')
        GROUP BY c.category_id
        HAVING pending_cards >= ?
        ORDER BY pending_cards DESC
        """,
        (PENDING_THRESHOLD,),
    )


def render_dashboard(rows: list[sqlite3.Row]) -> str:
    lines = [
        f"# Law Study Progress Dashboard",
        "",
        f"- 갱신: {datetime.now().isoformat(timespec='seconds')}",
        "- 기준 DB: `.agent/state/progress.sqlite`",
        "",
        "| category | 과목군 | 과목 | 쟁점 | 문제 | 약점 | Anki 대기 |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        issue_text = f"{r['done_issues']}/{r['issue_count']}" if r["issue_count"] else "0/0"
        problem_text = f"{r['done_problems']}/{r['problem_count']}" if r["problem_count"] else "0/0"
        lines.append(
            f"| {r['category_id']} | {r['subject_group']} | {r['subject']} | "
            f"{issue_text} | {problem_text} | {r['weak_count']} | {r['pending_cards']} |"
        )
    return "\n".join(lines) + "\n"


def render_today(rows: list[sqlite3.Row], overdue: list[sqlite3.Row], weak: list[sqlite3.Row], notice: list[sqlite3.Row]) -> str:
    today = date.today().isoformat()
    lines = [
        f"# {today} 오늘 공부 계획",
        "",
        "## 1. 진도 현황",
        "",
        "| category | 쟁점 | 문제 | 약점 | Anki 대기 |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['category_id']} | {r['done_issues']}/{r['issue_count']} | "
            f"{r['done_problems']}/{r['problem_count']} | {r['weak_count']} | {r['pending_cards']} |"
        )
    lines.extend(["", "## 2. 오늘 복습"])
    if overdue:
        for r in overdue[:10]:
            lines.append(f"- {r['issue_id']} ({r['review_type']}): {r['reason'] or '사유 미기재'}")
    else:
        lines.append("- 예정된 overdue 복습 없음")
    lines.extend(["", "## 3. 약점 경고"])
    if weak:
        for r in weak[:10]:
            lines.append(f"- {r['issue_id']}: {r['main_weakness'] or '약점 미기재'} / 다음 조치: {r['next_action'] or '미지정'}")
    else:
        lines.append("- severity가 기록된 약점 없음")
    lines.extend(["", "## 4. Anki 업데이트 상태"])
    if notice:
        for r in notice:
            lines.append(f"- {r['category_id']}: pending {r['pending_cards']}장, deck `{r['anki_deck']}`")
    else:
        lines.append("- pending threshold를 넘긴 category 없음")
    return "\n".join(lines) + "\n"


def render_review_queue(overdue: list[sqlite3.Row]) -> str:
    lines = ["# Law Study Review Queue", "", f"- 갱신: {datetime.now().isoformat(timespec='seconds')}", ""]
    if not overdue:
        lines.append("overdue 복습 없음")
        return "\n".join(lines) + "\n"
    lines.extend(["| due | priority | category | issue | type | reason |", "|---|---:|---|---|---|---|"])
    for r in overdue:
        lines.append(f"| {r['due_date']} | {r['priority']} | {r['category_id'] or ''} | {r['issue_id']} | {r['review_type']} | {r['reason'] or ''} |")
    return "\n".join(lines) + "\n"


def render_weak_points(weak: list[sqlite3.Row]) -> str:
    lines = ["# Law Study Weak Points", "", f"- 갱신: {datetime.now().isoformat(timespec='seconds')}", ""]
    if not weak:
        lines.append("기록된 약점 없음")
        return "\n".join(lines) + "\n"
    lines.extend(["| severity | category | issue | errors | repeat | weakness | next |", "|---:|---|---|---:|---:|---|---|"])
    for r in weak:
        lines.append(
            f"| {r['severity'] or 0} | {r['category_id'] or ''} | {r['issue_id']} | "
            f"{r['error_count'] or 0} | {r['repeat_error_count'] or 0} | "
            f"{r['main_weakness'] or ''} | {r['next_action'] or ''} |"
        )
    return "\n".join(lines) + "\n"


def render_anki_notice(notice: list[sqlite3.Row]) -> str:
    lines = ["# Anki 업데이트 필요", "", f"- 갱신: {datetime.now().isoformat(timespec='seconds')}", ""]
    if not notice:
        lines.append("현재 기준으로 Anki batch 생성이 필요한 category 없음")
        return "\n".join(lines) + "\n"
    for r in notice:
        lines.extend(
            [
                f"## {r['category_id']}",
                "",
                f"- deck: `{r['anki_deck']}`",
                f"- pending: {r['pending_cards']}장",
                f"- 마지막 batch: {r['last_batch_at'] or '기록 없음'}",
                f"- 권장 실행: `python .agent/scripts/generate_anki_batch.py --category {r['category_id']} --limit 50`",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}")
        print("Run: python .agent/scripts/init_law_study_db.py")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        categories = category_rows(conn)
        overdue = overdue_rows(conn)
        weak = weak_rows(conn)
        notice = anki_notice_rows(conn)
    finally:
        conn.close()

    write(STATE_DIR / "law_study_progress_dashboard.md", render_dashboard(categories))
    write(STATE_DIR / "law_study_today_plan.md", render_today(categories, overdue, weak, notice))
    write(STATE_DIR / "law_study_review_queue.md", render_review_queue(overdue))
    write(STATE_DIR / "law_study_weak_points.md", render_weak_points(weak))
    write(STATE_DIR / "law_study_anki_update_notice.md", render_anki_notice(notice))
    print("Generated .agent/state/law_study_*.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
