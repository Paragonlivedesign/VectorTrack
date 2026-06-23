from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from vectortrack.db.repository import Repository
from vectortrack.db.schema import SCHEMA_VERSION


def test_schema_user_version_after_init(tmp_path):
    db_file = tmp_path / "vectortrack.db"
    legacy_file = tmp_path / "sessions.db"
    Repository(database_path=db_file, legacy_database_path=legacy_file)

    with sqlite3.connect(str(db_file)) as conn:
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    assert version == SCHEMA_VERSION


def test_legacy_sessions_migrated_once(tmp_path):
    legacy_db = tmp_path / "sessions.db"
    with sqlite3.connect(str(legacy_db)) as conn:
        conn.execute(
            """
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                active_duration REAL NOT NULL,
                hourly_rate REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO sessions(project_id, file_path, start_time, end_time, active_duration, hourly_rate)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "MIG-001",
                "I:/legacy/file.vwx",
                datetime.now(timezone.utc).isoformat(),
                None,
                1800.0,
                120.0,
            ),
        )

    db_file = tmp_path / "vectortrack.db"
    first_repo = Repository(database_path=db_file, legacy_database_path=legacy_db)
    assert len(first_repo.list_sessions(project_id="MIG-001", include_open=True)) == 1

    second_repo = Repository(database_path=db_file, legacy_database_path=legacy_db)
    assert len(second_repo.list_sessions(project_id="MIG-001", include_open=True)) == 1
