#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mark a generated Anki batch as imported and archive its CSV with file-op logging."""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / ".agent" / "state" / "progress.sqlite"
EXPORTED_DIR = ROOT / "outputs" / "anki" / "law_study_exported"
LOG_HELPER = ROOT / ".agent" / "scripts" / "log_file_op.py"


def find_batch(conn: sqlite3.Connection, batch_id: str | None, file_path: str | None) -> sqlite3.Row | None:
    if batch_id:
        return conn.execute("SELECT * FROM anki_batches WHERE batch_id = ?", (batch_id,)).fetchone()
    if file_path:
        path = str(Path(file_path))
        return conn.execute(
            "SELECT * FROM anki_batches WHERE file_path = ? OR file_path LIKE ?",
            (path, f"%{Path(path).name}"),
        ).fetchone()
    return None


def archive_file(src: Path, batch_id: str) -> Path:
    dst = EXPORTED_DIR / src.name
    cmd = [
        sys.executable,
        str(LOG_HELPER),
        "--op",
        "move",
        "--src",
        str(src),
        "--dst",
        str(dst),
        "--reason",
        "law study Anki batch imported",
        "--task-id",
        batch_id,
        "--execute",
    ]
    subprocess.run(cmd, check=True)
    return dst


def main() -> int:
    parser = argparse.ArgumentParser(description="Mark a law-study Anki batch as imported.")
    parser.add_argument("--batch-id")
    parser.add_argument("--file")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--no-move", action="store_true", help="Update DB only; do not move the CSV.")
    args = parser.parse_args()

    if not args.batch_id and not args.file:
        parser.error("Provide --batch-id or --file")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        batch = find_batch(conn, args.batch_id, args.file)
        if batch is None:
            print("Batch not found.")
            return 1

        now = datetime.now().isoformat(timespec="seconds")
        stored_path = ROOT / batch["file_path"]
        final_path = stored_path
        if not args.no_move and stored_path.exists():
            final_path = archive_file(stored_path, batch["batch_id"])

        conn.execute(
            "UPDATE anki_batches SET status = 'imported', imported_at = ?, file_path = ? WHERE batch_id = ?",
            (now, str(final_path.relative_to(ROOT)), batch["batch_id"]),
        )
        conn.execute(
            "UPDATE anki_candidates SET status = 'exported', exported_at = ?, updated_at = ? WHERE batch_id = ?",
            (now, now, batch["batch_id"]),
        )
        conn.commit()
        print(f"Imported: {batch['batch_id']}")
        print(f"File: {final_path}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
