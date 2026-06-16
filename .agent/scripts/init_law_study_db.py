#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Initialize the law-study SQLite ledger without overwriting existing state."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / ".agent" / "state" / "progress.sqlite"
DATA_DIR = ROOT / ".agent" / "data"


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
  category_id TEXT PRIMARY KEY,
  subject_group TEXT NOT NULL,
  subject TEXT NOT NULL,
  category_name TEXT NOT NULL,
  anki_deck TEXT NOT NULL,
  weekly_export_limit INTEGER DEFAULT 80,
  daily_new_limit_hint INTEGER DEFAULT 25,
  status TEXT DEFAULT 'active',
  planned_start_date TEXT,
  planned_end_date TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS issues (
  issue_id TEXT PRIMARY KEY,
  subject_group TEXT NOT NULL,
  subject TEXT NOT NULL,
  category_id TEXT NOT NULL,
  area TEXT,
  topic TEXT,
  title TEXT NOT NULL,
  source_file TEXT,
  source_location TEXT,
  difficulty INTEGER,
  importance INTEGER,
  status TEXT DEFAULT 'not_started',
  anki_export_status TEXT DEFAULT 'not_exported',
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS problems (
  problem_id TEXT PRIMARY KEY,
  subject_group TEXT NOT NULL,
  subject TEXT NOT NULL,
  category_id TEXT,
  area TEXT,
  topic TEXT,
  problem_file TEXT NOT NULL,
  estimated_minutes INTEGER,
  difficulty INTEGER,
  status TEXT DEFAULT 'not_started',
  planned_date TEXT,
  completed_at TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS problem_issues (
  problem_id TEXT NOT NULL,
  issue_id TEXT NOT NULL,
  expected_weight REAL DEFAULT 1.0,
  PRIMARY KEY (problem_id, issue_id)
);

CREATE TABLE IF NOT EXISTS study_sessions (
  session_id TEXT PRIMARY KEY,
  session_date TEXT NOT NULL,
  subject_group TEXT,
  subject TEXT,
  category_id TEXT,
  study_range TEXT,
  minutes INTEGER,
  session_type TEXT,
  notes TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS attempts (
  attempt_id TEXT PRIMARY KEY,
  problem_id TEXT NOT NULL,
  answer_file TEXT NOT NULL,
  review_md TEXT,
  review_json TEXT,
  attempt_date TEXT NOT NULL,
  subject_group TEXT,
  subject TEXT,
  category_id TEXT,
  total_score REAL,
  issue_spotting_score REAL,
  keyword_score REAL,
  structure_score REAL,
  conclusion_score REAL,
  application_score REAL,
  time_spent_minutes INTEGER,
  notes TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS issue_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  attempt_id TEXT NOT NULL,
  problem_id TEXT NOT NULL,
  issue_id TEXT NOT NULL,
  category_id TEXT,
  detected INTEGER,
  keyword_match REAL,
  structure_match REAL,
  conclusion_match INTEGER,
  application_score REAL,
  missing_keywords TEXT,
  missing_structure TEXT,
  application_feedback TEXT,
  source_file TEXT,
  source_location TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS keyword_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  attempt_id TEXT NOT NULL,
  issue_id TEXT NOT NULL,
  keyword TEXT NOT NULL,
  matched INTEGER,
  matched_alias TEXT,
  source_file TEXT,
  source_location TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS conclusion_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  attempt_id TEXT NOT NULL,
  issue_id TEXT NOT NULL,
  expected_pattern TEXT,
  user_conclusion TEXT,
  match_status TEXT,
  source_file TEXT,
  source_location TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS review_queue (
  queue_id TEXT PRIMARY KEY,
  issue_id TEXT NOT NULL,
  problem_id TEXT,
  category_id TEXT,
  due_date TEXT NOT NULL,
  review_type TEXT NOT NULL,
  reason TEXT,
  priority INTEGER DEFAULT 50,
  status TEXT DEFAULT 'scheduled',
  created_from_attempt_id TEXT,
  completed_at TEXT,
  result_score REAL,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS weak_points (
  issue_id TEXT PRIMARY KEY,
  subject_group TEXT,
  subject TEXT,
  category_id TEXT,
  topic TEXT,
  error_count INTEGER DEFAULT 0,
  repeat_error_count INTEGER DEFAULT 0,
  last_error_date TEXT,
  avg_keyword_score REAL,
  avg_structure_score REAL,
  avg_application_score REAL,
  main_weakness TEXT,
  next_action TEXT,
  severity INTEGER,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS anki_candidates (
  card_id TEXT PRIMARY KEY,
  note_key TEXT UNIQUE NOT NULL,
  issue_id TEXT NOT NULL,
  category_id TEXT,
  source_attempt_id TEXT,
  card_type TEXT NOT NULL,
  deck TEXT NOT NULL,
  front TEXT NOT NULL,
  back TEXT NOT NULL,
  extra TEXT,
  tags TEXT,
  source_file TEXT,
  source_location TEXT,
  status TEXT DEFAULT 'pending',
  export_priority INTEGER DEFAULT 50,
  front_hash TEXT,
  batch_id TEXT,
  exported_at TEXT,
  updated_at TEXT,
  anki_guid TEXT
);

CREATE TABLE IF NOT EXISTS anki_batches (
  batch_id TEXT PRIMARY KEY,
  category_id TEXT NOT NULL,
  subject_group TEXT,
  deck_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  card_count INTEGER DEFAULT 0,
  new_card_count INTEGER DEFAULT 0,
  update_card_count INTEGER DEFAULT 0,
  repeated_error_card_count INTEGER DEFAULT 0,
  generated_at TEXT NOT NULL,
  imported_at TEXT,
  status TEXT DEFAULT 'generated',
  notes TEXT
);

CREATE TABLE IF NOT EXISTS weekly_stats (
  week_id TEXT PRIMARY KEY,
  start_date TEXT NOT NULL,
  end_date TEXT NOT NULL,
  subject_group TEXT,
  subject TEXT,
  category_id TEXT,
  problems_attempted INTEGER DEFAULT 0,
  avg_total_score REAL,
  weak_issue_count INTEGER DEFAULT 0,
  anki_exported_count INTEGER DEFAULT 0,
  created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_issues_category ON issues(category_id);
CREATE INDEX IF NOT EXISTS idx_problems_category ON problems(category_id);
CREATE INDEX IF NOT EXISTS idx_review_queue_due ON review_queue(status, due_date, priority);
CREATE INDEX IF NOT EXISTS idx_anki_candidates_status_category ON anki_candidates(status, category_id, export_priority);
CREATE INDEX IF NOT EXISTS idx_attempts_problem_date ON attempts(problem_id, attempt_date);
PRAGMA user_version = 1;
"""


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f) if any((v or "").strip() for v in row.values())]


def to_int(value: str | None, default: int | None = None) -> int | None:
    if value is None or str(value).strip() == "":
        return default
    return int(value)


def import_categories(conn: sqlite3.Connection, rows: list[dict[str, str]]) -> int:
    ts = now_iso()
    count = 0
    for row in rows:
        conn.execute(
            """
            INSERT INTO categories (
              category_id, subject_group, subject, category_name, anki_deck,
              weekly_export_limit, daily_new_limit_hint, status,
              planned_start_date, planned_end_date, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(category_id) DO UPDATE SET
              subject_group=excluded.subject_group,
              subject=excluded.subject,
              category_name=excluded.category_name,
              anki_deck=excluded.anki_deck,
              weekly_export_limit=excluded.weekly_export_limit,
              daily_new_limit_hint=excluded.daily_new_limit_hint,
              status=excluded.status,
              planned_start_date=excluded.planned_start_date,
              planned_end_date=excluded.planned_end_date,
              updated_at=excluded.updated_at
            """,
            (
                row["category_id"],
                row["subject_group"],
                row["subject"],
                row["category_name"],
                row["anki_deck"],
                to_int(row.get("weekly_export_limit"), 80),
                to_int(row.get("daily_new_limit_hint"), 25),
                row.get("status") or "active",
                row.get("planned_start_date") or None,
                row.get("planned_end_date") or None,
                ts,
                ts,
            ),
        )
        count += 1
    return count


def import_issues(conn: sqlite3.Connection, rows: list[dict[str, str]]) -> int:
    ts = now_iso()
    count = 0
    for row in rows:
        if not row.get("issue_id"):
            continue
        conn.execute(
            """
            INSERT INTO issues (
              issue_id, subject_group, subject, category_id, area, topic, title,
              source_file, source_location, difficulty, importance, status,
              created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(issue_id) DO UPDATE SET
              subject_group=excluded.subject_group,
              subject=excluded.subject,
              category_id=excluded.category_id,
              area=excluded.area,
              topic=excluded.topic,
              title=excluded.title,
              source_file=excluded.source_file,
              source_location=excluded.source_location,
              difficulty=excluded.difficulty,
              importance=excluded.importance,
              status=excluded.status,
              updated_at=excluded.updated_at
            """,
            (
                row["issue_id"],
                row["subject_group"],
                row["subject"],
                row["category_id"],
                row.get("area") or None,
                row.get("topic") or None,
                row["title"],
                row.get("source_file") or None,
                row.get("source_location") or None,
                to_int(row.get("difficulty")),
                to_int(row.get("importance")),
                row.get("status") or "not_started",
                ts,
                ts,
            ),
        )
        count += 1
    return count


def import_problems(conn: sqlite3.Connection, rows: list[dict[str, str]]) -> int:
    ts = now_iso()
    count = 0
    for row in rows:
        if not row.get("problem_id"):
            continue
        conn.execute(
            """
            INSERT INTO problems (
              problem_id, subject_group, subject, category_id, area, topic,
              problem_file, estimated_minutes, difficulty, status, planned_date,
              created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(problem_id) DO UPDATE SET
              subject_group=excluded.subject_group,
              subject=excluded.subject,
              category_id=excluded.category_id,
              area=excluded.area,
              topic=excluded.topic,
              problem_file=excluded.problem_file,
              estimated_minutes=excluded.estimated_minutes,
              difficulty=excluded.difficulty,
              status=excluded.status,
              planned_date=excluded.planned_date,
              updated_at=excluded.updated_at
            """,
            (
                row["problem_id"],
                row["subject_group"],
                row["subject"],
                row.get("category_id") or None,
                row.get("area") or None,
                row.get("topic") or None,
                row["problem_file"],
                to_int(row.get("estimated_minutes")),
                to_int(row.get("difficulty")),
                row.get("status") or "not_started",
                row.get("planned_date") or None,
                ts,
                ts,
            ),
        )
        conn.execute("DELETE FROM problem_issues WHERE problem_id = ?", (row["problem_id"],))
        issue_ids = [v.strip() for v in (row.get("expected_issue_ids") or "").split(";") if v.strip()]
        for issue_id in issue_ids:
            conn.execute(
                "INSERT OR IGNORE INTO problem_issues(problem_id, issue_id, expected_weight) VALUES (?, ?, 1.0)",
                (row["problem_id"], issue_id),
            )
        count += 1
    return count


def initialize(db_path: Path, schema_only: bool = False) -> dict[str, int | str]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        imported = {"categories": 0, "issues": 0, "problems": 0}
        if not schema_only:
            imported["categories"] = import_categories(conn, read_rows(DATA_DIR / "category_catalog.csv"))
            imported["issues"] = import_issues(conn, read_rows(DATA_DIR / "issue_catalog.csv"))
            imported["problems"] = import_problems(conn, read_rows(DATA_DIR / "problem_catalog.csv"))
        conn.commit()
        return {"db": str(db_path), **imported}
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize law-study SQLite tables and import base catalogs.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite path. Default: .agent/state/progress.sqlite")
    parser.add_argument("--schema-only", action="store_true", help="Create tables only; skip CSV import.")
    args = parser.parse_args()

    result = initialize(Path(args.db), schema_only=args.schema_only)
    print(f"DB: {result['db']}")
    print(f"categories imported: {result['categories']}")
    print(f"issues imported: {result['issues']}")
    print(f"problems imported: {result['problems']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
