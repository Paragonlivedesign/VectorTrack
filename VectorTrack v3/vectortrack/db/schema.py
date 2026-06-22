"""
Database schema and migrations for VectorTrack v4 foundation layer.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 3
LEGACY_SOURCE = "legacy-v1"


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _create_schema_v2(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS billable_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            project_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            hourly_rate REAL NOT NULL DEFAULT 0.0,
            is_active INTEGER NOT NULL DEFAULT 1,
            is_locked INTEGER NOT NULL DEFAULT 0,
            locked_at TEXT,
            invoice_number TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS project_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            alias_pattern TEXT NOT NULL,
            is_regex INTEGER NOT NULL DEFAULT 0,
            priority INTEGER NOT NULL DEFAULT 100,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES billable_projects(id) ON DELETE CASCADE,
            UNIQUE (project_id, alias_pattern)
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_alias TEXT,
            machine_id TEXT,
            source TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            hourly_rate REAL NOT NULL DEFAULT 0.0,
            live_duration REAL NOT NULL DEFAULT 0.0,
            log_history_duration REAL NOT NULL DEFAULT 0.0,
            log_current_open_hours REAL NOT NULL DEFAULT 0.0,
            balance_delta_hours REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_open_identity
        ON sessions(project_id, file_path, machine_id, source)
        WHERE end_time IS NULL;

        CREATE TABLE IF NOT EXISTS session_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            source TEXT,
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS log_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS project_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES billable_projects(id) ON DELETE CASCADE
        );
        """
    )


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(str(row[1]) == column for row in rows)


def _migrate_v3_lock_fields(conn: sqlite3.Connection) -> None:
    if not _column_exists(conn, "billable_projects", "is_locked"):
        conn.execute(
            "ALTER TABLE billable_projects ADD COLUMN is_locked INTEGER NOT NULL DEFAULT 0"
        )
    if not _column_exists(conn, "billable_projects", "locked_at"):
        conn.execute("ALTER TABLE billable_projects ADD COLUMN locked_at TEXT")
    if not _column_exists(conn, "billable_projects", "invoice_number"):
        conn.execute("ALTER TABLE billable_projects ADD COLUMN invoice_number TEXT")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS project_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES billable_projects(id) ON DELETE CASCADE
        );
        """
    )


def _legacy_sessions_already_migrated(conn: sqlite3.Connection) -> bool:
    if not _table_exists(conn, "app_settings"):
        return False
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key='legacy_v1_sessions_migrated'"
    ).fetchone()
    return row is not None and str(row["value"]) == "1"


def _set_legacy_migration_marker(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO app_settings(key, value, updated_at)
        VALUES('legacy_v1_sessions_migrated', '1', CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value,
            updated_at=excluded.updated_at
        """
    )


def _migrate_legacy_v1_sessions(conn: sqlite3.Connection, legacy_db_file: Path | None) -> None:
    if legacy_db_file is None or not legacy_db_file.exists():
        return

    if _legacy_sessions_already_migrated(conn):
        return

    with sqlite3.connect(str(legacy_db_file)) as legacy_conn:
        legacy_conn.row_factory = sqlite3.Row
        if not _table_exists(legacy_conn, "sessions"):
            return

        rows = legacy_conn.execute(
            """
            SELECT
                project_id,
                file_path,
                start_time,
                end_time,
                active_duration,
                hourly_rate
            FROM sessions
            """
        ).fetchall()

    if not rows:
        _set_legacy_migration_marker(conn)
        return

    conn.execute(
        """
        INSERT OR IGNORE INTO log_sources(source, description)
        VALUES(?, ?)
        """,
        (LEGACY_SOURCE, "Imported from v1 sessions.db"),
    )

    for row in rows:
        file_path = str(row["file_path"])
        file_alias = Path(file_path).name if file_path else None
        inserted = conn.execute(
            """
            INSERT INTO sessions(
                project_id,
                file_path,
                file_alias,
                machine_id,
                source,
                start_time,
                end_time,
                hourly_rate,
                live_duration,
                log_history_duration,
                log_current_open_hours,
                balance_delta_hours
            )
            VALUES(?, ?, ?, NULL, ?, ?, ?, ?, ?, 0.0, 0.0, 0.0)
            """,
            (
                row["project_id"],
                file_path,
                file_alias,
                LEGACY_SOURCE,
                row["start_time"],
                row["end_time"],
                float(row["hourly_rate"] or 0.0),
                float(row["active_duration"] or 0.0),
            ),
        )
        conn.execute(
            """
            INSERT INTO session_audit(session_id, action, old_values, new_values, source)
            VALUES(?, 'migrated_v1', NULL, NULL, ?)
            """,
            (inserted.lastrowid, LEGACY_SOURCE),
        )

    _set_legacy_migration_marker(conn)


def migrate(conn: sqlite3.Connection, legacy_db_file: Path | None = None) -> None:
    """
    Bring a database connection up to SCHEMA_VERSION.

    The v2 migration includes optional import of sessions from a legacy v1
    `sessions.db` file if present.
    """
    current_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if current_version >= SCHEMA_VERSION:
        return

    if current_version < 2:
        _create_schema_v2(conn)
        _migrate_legacy_v1_sessions(conn, legacy_db_file)
        conn.execute("PRAGMA user_version = 2")
        current_version = 2

    if current_version < 3:
        _migrate_v3_lock_fields(conn)
        conn.execute("PRAGMA user_version = 3")


def init_database(db_file: Path, legacy_db_file: Path | None = None) -> None:
    """Create and migrate the database file to the latest schema."""
    db_file.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        migrate(conn, legacy_db_file=legacy_db_file)
        conn.commit()
