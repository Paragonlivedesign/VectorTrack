"""Session persistence extracted from Repository."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from vectortrack.models import TimeSession


class SessionRepository:
    """Session-focused database operations."""

    def __init__(self, connect: callable) -> None:
        self._connect = connect

    def upsert_open_session(self, session: TimeSession) -> TimeSession:
        row = session.to_row()
        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT id FROM sessions
                WHERE project_id=? AND file_path=? AND machine_id=? AND source=? AND end_time IS NULL
                """,
                (row["project_id"], row["file_path"], row["machine_id"], row["source"]),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE sessions SET
                        hourly_rate=?, rate_overridden=?, live_duration=?,
                        log_history_duration=?, log_current_open_hours=?, balance_delta_hours=?,
                        updated_at=?
                    WHERE id=?
                    """,
                    (
                        row["hourly_rate"],
                        row.get("rate_overridden", 0),
                        row["live_duration"],
                        row.get("log_history_duration", 0.0),
                        row.get("log_current_open_hours", 0.0),
                        row.get("balance_delta_hours", 0.0),
                        datetime.now(timezone.utc).isoformat(),
                        existing["id"],
                    ),
                )
                saved = conn.execute("SELECT * FROM sessions WHERE id=?", (existing["id"],)).fetchone()
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO sessions(
                        project_id, file_path, file_alias, machine_id, source,
                        start_time, end_time, hourly_rate, rate_overridden,
                        live_duration, log_history_duration, log_current_open_hours,
                        balance_delta_hours, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["project_id"],
                        row["file_path"],
                        row.get("file_alias"),
                        row["machine_id"],
                        row["source"],
                        row["start_time"],
                        row["end_time"],
                        row["hourly_rate"],
                        row.get("rate_overridden", 0),
                        row["live_duration"],
                        row.get("log_history_duration", 0.0),
                        row.get("log_current_open_hours", 0.0),
                        row.get("balance_delta_hours", 0.0),
                        row.get("created_at") or datetime.now(timezone.utc).isoformat(),
                        row.get("updated_at") or datetime.now(timezone.utc).isoformat(),
                    ),
                )
                saved = conn.execute(
                    "SELECT * FROM sessions WHERE id=?",
                    (cursor.lastrowid,),
                ).fetchone()
        return TimeSession.from_row(saved)

    def list_sessions(
        self,
        *,
        project_id: str | None = None,
        include_open: bool = True,
        limit: int = 1000,
    ) -> list[TimeSession]:
        query = "SELECT * FROM sessions WHERE 1=1"
        params: list[Any] = []
        if project_id is not None:
            query += " AND project_id=?"
            params.append(project_id)
        if not include_open:
            query += " AND end_time IS NOT NULL"
        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [TimeSession.from_row(row) for row in rows]
