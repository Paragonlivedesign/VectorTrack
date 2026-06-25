"""
Repository abstraction for VectorTrack 0.5 foundation data access.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

from vectortrack import config
from vectortrack.db.schema import init_database
from datetime import datetime, timedelta, timezone

from vectortrack.models import AliasRule, BillableProject, Client, TimeSession
from vectortrack.services.vw_identity import local_machine_id


from vectortrack.db.rate_resolver import resolve_rate_for_project
from vectortrack.db.session_repository import SessionRepository


class Repository:
    RATE_STRATEGY_PROJECT = "project_rate"
    RATE_STRATEGY_KEEP = "keep_rate"
    RATE_STRATEGY_SPLIT = "split"

    def __init__(
        self,
        database_path: Path | None = None,
        legacy_database_path: Path | None = None,
        default_hourly_rate: float | None = None,
    ) -> None:
        self.database_path = database_path or config.db_path()
        self.legacy_database_path = legacy_database_path or config.legacy_db_path()
        self.default_hourly_rate = (
            float(default_hourly_rate)
            if default_hourly_rate is not None
            else float(config.DEFAULT_HOURLY_RATE)
        )
        init_database(self.database_path, legacy_db_file=self.legacy_database_path)
        self._sessions = SessionRepository(self._connect)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.database_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    # Clients
    def create_client(self, client: Client) -> Client:
        row = client.to_row()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO clients(name, code, is_active, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    row["name"],
                    row["code"],
                    row["is_active"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            created = conn.execute(
                "SELECT * FROM clients WHERE id=?",
                (cursor.lastrowid,),
            ).fetchone()
        return Client.from_row(created)

    def list_clients(self, active_only: bool = False) -> list[Client]:
        query = "SELECT * FROM clients"
        params: list[Any] = []
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name COLLATE NOCASE ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [Client.from_row(row) for row in rows]

    def get_client(self, client_id: int) -> Optional[Client]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        return Client.from_row(row) if row else None

    def find_client_by_code(self, code: str) -> Optional[Client]:
        normalized = str(code or "").strip()
        if not normalized:
            return None
        for client in self.list_clients(active_only=False):
            if client.code and client.code.strip().lower() == normalized.lower():
                return client
        return None

    def find_client_by_normalized_name(self, name: str) -> Optional[Client]:
        target = str(name or "").strip().lower()
        if not target:
            return None
        for client in self.list_clients(active_only=False):
            if client.name.strip().lower() == target:
                return client
        return None

    def update_client(self, client: Client) -> Client:
        if client.id is None:
            raise ValueError("client.id is required for update")

        row = client.to_row()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE clients
                SET name=?, code=?, is_active=?, updated_at=?
                WHERE id=?
                """,
                (
                    row["name"],
                    row["code"],
                    row["is_active"],
                    row["updated_at"],
                    client.id,
                ),
            )
            updated = conn.execute(
                "SELECT * FROM clients WHERE id=?",
                (client.id,),
            ).fetchone()
        if not updated:
            raise ValueError(f"Client not found: {client.id}")
        return Client.from_row(updated)

    # Billable projects
    def create_project(self, project: BillableProject) -> BillableProject:
        row = project.to_row()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO billable_projects(
                    client_id, project_code, name, hourly_rate,
                    is_active, is_locked, locked_at, invoice_number,
                    created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["client_id"],
                    row["project_code"],
                    row["name"],
                    row["hourly_rate"],
                    row["is_active"],
                    row["is_locked"],
                    row["locked_at"],
                    row["invoice_number"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            created = conn.execute(
                "SELECT * FROM billable_projects WHERE id=?",
                (cursor.lastrowid,),
            ).fetchone()
        return BillableProject.from_row(created)

    def update_project(self, project: BillableProject) -> BillableProject:
        if project.id is None:
            raise ValueError("project.id is required for update")
        if project.is_locked:
            raise PermissionError(f"Project '{project.project_code}' is locked for billing")

        row = project.to_row()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE billable_projects
                SET client_id=?, project_code=?, name=?, hourly_rate=?,
                    is_active=?, updated_at=?
                WHERE id=? AND is_locked=0
                """,
                (
                    row["client_id"],
                    row["project_code"],
                    row["name"],
                    row["hourly_rate"],
                    row["is_active"],
                    row["updated_at"],
                    project.id,
                ),
            )
            updated = conn.execute(
                "SELECT * FROM billable_projects WHERE id=?",
                (project.id,),
            ).fetchone()
        if not updated:
            raise PermissionError(f"Project '{project.project_code}' is locked or missing")
        return BillableProject.from_row(updated)

    def is_project_locked(self, project_code: str) -> bool:
        project = self.get_project_by_code(project_code)
        return bool(project and project.is_locked)

    def set_project_lock(
        self,
        project_code: str,
        locked: bool,
        invoice_number: str | None = None,
    ) -> BillableProject:
        project = self.get_project_by_code(project_code)
        if project is None or project.id is None:
            raise ValueError(f"Project not found: {project_code}")

        old_values = {
            "is_locked": project.is_locked,
            "locked_at": project.locked_at,
            "invoice_number": project.invoice_number,
        }
        now = datetime.now(timezone.utc).isoformat()
        new_locked_at = now if locked else None
        new_invoice = invoice_number if locked else project.invoice_number

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE billable_projects
                SET is_locked=?, locked_at=?, invoice_number=?, updated_at=?
                WHERE id=?
                """,
                (
                    int(locked),
                    new_locked_at,
                    new_invoice,
                    now,
                    project.id,
                ),
            )
            updated = conn.execute(
                "SELECT * FROM billable_projects WHERE id=?",
                (project.id,),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO project_audit(project_id, action, old_values, new_values)
                VALUES(?, ?, ?, ?)
                """,
                (
                    project.id,
                    "locked" if locked else "unlocked",
                    json.dumps(old_values),
                    json.dumps(
                        {
                            "is_locked": locked,
                            "locked_at": new_locked_at,
                            "invoice_number": new_invoice,
                        }
                    ),
                ),
            )
        return BillableProject.from_row(updated)

    def add_manual_session(self, session: TimeSession) -> TimeSession:
        if self.is_project_locked(session.project_id):
            raise PermissionError(f"Project '{session.project_id}' is locked for billing")
        end_time = session.end_time
        session.end_time = None
        stored = self.upsert_open_session(session)
        if stored.id is not None and end_time is not None:
            closed = self.close_session(stored.id, end_time.isoformat())
            if closed and closed.id is not None:
                self.add_session_audit(
                    session_id=closed.id,
                    action="manual_entry",
                    new_values=closed.to_dict(),
                    source="manual",
                )
            return closed or stored
        return stored

    def list_projects(
        self, client_id: int | None = None, active_only: bool = False
    ) -> list[BillableProject]:
        clauses: list[str] = []
        params: list[Any] = []
        if client_id is not None:
            clauses.append("client_id = ?")
            params.append(client_id)
        if active_only:
            clauses.append("is_active = 1")

        query = "SELECT * FROM billable_projects"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY name COLLATE NOCASE ASC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [BillableProject.from_row(row) for row in rows]

    def get_project(self, project_id: int) -> Optional[BillableProject]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM billable_projects WHERE id=?",
                (project_id,),
            ).fetchone()
        return BillableProject.from_row(row) if row else None

    def get_project_by_code(self, project_code: str) -> Optional[BillableProject]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM billable_projects WHERE project_code=?",
                (project_code,),
            ).fetchone()
        return BillableProject.from_row(row) if row else None

    def count_sessions_for_project(self, project_code: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM sessions WHERE project_id=?",
                (project_code,),
            ).fetchone()
        return int(row["count"]) if row else 0

    def delete_project(self, project_code: str) -> None:
        project = self.get_project_by_code(project_code)
        if project is None or project.id is None:
            raise ValueError(f"Project not found: {project_code}")

        with self._connect() as conn:
            open_rows = conn.execute(
                """
                SELECT id, file_path, machine_id, source, live_duration
                FROM sessions
                WHERE project_id=? AND end_time IS NULL
                """,
                (project_code,),
            ).fetchall()
            for row in open_rows:
                existing = conn.execute(
                    """
                    SELECT id, live_duration FROM sessions
                    WHERE project_id=''
                      AND file_path=?
                      AND machine_id IS ?
                      AND source IS ?
                      AND end_time IS NULL
                    """,
                    (row["file_path"], row["machine_id"], row["source"]),
                ).fetchone()
                if existing:
                    merged_duration = float(existing["live_duration"] or 0.0) + float(
                        row["live_duration"] or 0.0
                    )
                    conn.execute(
                        "UPDATE sessions SET live_duration=? WHERE id=?",
                        (merged_duration, existing["id"]),
                    )
                    conn.execute("DELETE FROM sessions WHERE id=?", (row["id"],))
                else:
                    conn.execute(
                        "UPDATE sessions SET project_id='' WHERE id=?",
                        (row["id"],),
                    )

            conn.execute(
                "UPDATE sessions SET project_id='' WHERE project_id=? AND end_time IS NOT NULL",
                (project_code,),
            )
            conn.execute(
                "UPDATE session_adjustments SET project_id='' WHERE project_id=?",
                (project_code,),
            )
            for key in (
                f"budget_hours:{project_code}",
                f"budget_money:{project_code}",
                f"budget_type:{project_code}",
            ):
                conn.execute("DELETE FROM app_settings WHERE key=?", (key,))
            conn.execute("DELETE FROM billable_projects WHERE id=?", (project.id,))

    # Alias rules
    def upsert_alias_rule(self, rule: AliasRule) -> AliasRule:
        row = rule.to_row()
        with self._connect() as conn:
            if rule.id is None:
                cursor = conn.execute(
                    """
                    INSERT INTO project_aliases(
                        project_id, alias_pattern, is_regex, priority, is_active, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["project_id"],
                        row["alias_pattern"],
                        row["is_regex"],
                        row["priority"],
                        row["is_active"],
                        row["created_at"],
                    ),
                )
                target_id = cursor.lastrowid
            else:
                conn.execute(
                    """
                    UPDATE project_aliases
                    SET project_id=?, alias_pattern=?, is_regex=?, priority=?, is_active=?
                    WHERE id=?
                    """,
                    (
                        row["project_id"],
                        row["alias_pattern"],
                        row["is_regex"],
                        row["priority"],
                        row["is_active"],
                        rule.id,
                    ),
                )
                target_id = rule.id

            updated = conn.execute(
                "SELECT * FROM project_aliases WHERE id=?",
                (target_id,),
            ).fetchone()
        return AliasRule.from_row(updated)

    def list_alias_rules(
        self, project_id: int | None = None, active_only: bool = True
    ) -> list[AliasRule]:
        clauses: list[str] = []
        params: list[Any] = []
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if active_only:
            clauses.append("is_active = 1")

        query = "SELECT * FROM project_aliases"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY priority ASC, id ASC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [AliasRule.from_row(row) for row in rows]

    def resolve_project_by_file_alias(self, file_alias: str) -> Optional[BillableProject]:
        for rule in self.list_alias_rules(active_only=True):
            if self._matches_alias(rule, file_alias):
                return self.get_project(rule.project_id)
        return None

    @staticmethod
    def _matches_alias(rule: AliasRule, file_alias: str) -> bool:
        if rule.is_regex:
            return re.search(rule.alias_pattern, file_alias) is not None
        return rule.alias_pattern.lower() in file_alias.lower()

    def resolve_hourly_rate(
        self,
        project_id: str,
        *,
        override_rate: float | None = None,
    ) -> float:
        return resolve_rate_for_project(
            self,
            project_id,
            override_rate=override_rate,
        )

    def get_open_live_session(
        self,
        file_path: str,
        machine_id: str | None = None,
    ) -> Optional[TimeSession]:
        resolved_machine_id = local_machine_id() if machine_id is None else machine_id
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM sessions
                WHERE file_path=?
                  AND machine_id=?
                  AND source = 'live'
                  AND end_time IS NULL
                ORDER BY id DESC
                LIMIT 1
                """,
                (file_path, resolved_machine_id),
            ).fetchone()
        return TimeSession.from_row(row) if row else None

    def set_open_session_rate(self, file_path: str, hourly_rate: float) -> Optional[TimeSession]:
        existing = self.get_open_live_session(file_path)
        if not existing or existing.id is None:
            return None
        updated = TimeSession(
            id=existing.id,
            project_id=existing.project_id,
            file_path=existing.file_path,
            file_alias=existing.file_alias,
            machine_id=existing.machine_id,
            source=existing.source,
            start_time=existing.start_time,
            hourly_rate=float(hourly_rate),
            rate_overridden=True,
            live_duration=existing.live_duration,
            log_history_duration=existing.log_history_duration,
            log_current_open_hours=existing.log_current_open_hours,
            balance_delta_hours=existing.balance_delta_hours,
        )
        return self._update_open_session_fields(updated)

    def assign_file_to_project(
        self,
        file_path: str,
        new_project_id: str,
        *,
        rate_strategy: str = RATE_STRATEGY_PROJECT,
    ) -> tuple[Optional[TimeSession], bool]:
        """
        Reassign an open live session to a project.

        Returns (open_session, split_occurred).
        """
        existing = self.get_open_live_session(file_path)
        project_rate = self.resolve_hourly_rate(new_project_id)
        now_dt = datetime.now()
        now_iso = now_dt.isoformat()

        if rate_strategy == self.RATE_STRATEGY_SPLIT and existing and existing.id is not None:
            self.close_session(existing.id, now_iso)
            new_session = TimeSession(
                project_id=new_project_id,
                file_path=file_path,
                start_time=now_dt,
                hourly_rate=project_rate,
                rate_overridden=False,
                live_duration=timedelta(),
                source="live",
            )
            return self.upsert_open_session(new_session), True

        if existing and existing.id is not None:
            if rate_strategy == self.RATE_STRATEGY_KEEP:
                new_rate = existing.hourly_rate
                rate_overridden = True
            else:
                new_rate = project_rate
                rate_overridden = False
            updated = TimeSession(
                id=existing.id,
                project_id=new_project_id,
                file_path=existing.file_path,
                file_alias=existing.file_alias,
                machine_id=existing.machine_id,
                source=existing.source,
                start_time=existing.start_time,
                hourly_rate=new_rate,
                rate_overridden=rate_overridden,
                live_duration=existing.live_duration,
                log_history_duration=existing.log_history_duration,
                log_current_open_hours=existing.log_current_open_hours,
                balance_delta_hours=existing.balance_delta_hours,
            )
            return self._update_open_session_fields(updated), False

        return None, False

    def _update_open_session_fields(self, session: TimeSession) -> TimeSession:
        if session.id is None:
            raise ValueError("session.id is required for update")
        row = session.to_row()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET project_id=?, file_alias=?, start_time=?, hourly_rate=?, rate_overridden=?,
                    live_duration=?, log_history_duration=?, log_current_open_hours=?,
                    balance_delta_hours=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    row["project_id"],
                    row["file_alias"],
                    row["start_time"],
                    row["hourly_rate"],
                    row["rate_overridden"],
                    row["live_duration"],
                    row["log_history_duration"],
                    row["log_current_open_hours"],
                    row["balance_delta_hours"],
                    session.id,
                ),
            )
            current = conn.execute("SELECT * FROM sessions WHERE id=?", (session.id,)).fetchone()
        return TimeSession.from_row(current)

    # Sessions
    def start_session(self, tracking_state: Any) -> TimeSession:
        """
        Adapter for TrackingService.

        Accepts a tracking state object with `project_id`, `file_path`, and
        optional `started_at` / `tracked_seconds` fields.
        """
        started_at = getattr(tracking_state, "started_at", None) or datetime.now()
        tracked_seconds = float(getattr(tracking_state, "tracked_seconds", 0.0) or 0.0)
        session = TimeSession(
            project_id=str(getattr(tracking_state, "project_id", "")),
            file_path=str(getattr(tracking_state, "file_path", "")),
            start_time=started_at,
            hourly_rate=self.resolve_hourly_rate(str(getattr(tracking_state, "project_id", ""))),
            live_duration=timedelta(seconds=max(0.0, tracked_seconds)),
            source="live",
            machine_id=local_machine_id(),
        )
        return self.upsert_open_session(session)

    def update_session_duration(self, tracking_state: Any, _elapsed_seconds: float) -> Optional[TimeSession]:
        """
        Adapter for TrackingService duration ticks.

        TrackingService already updates `tracked_seconds` before calling this method,
        so this writes the current running total rather than incrementing here.
        """
        project_id = str(getattr(tracking_state, "project_id", ""))
        file_path = str(getattr(tracking_state, "file_path", ""))
        if not file_path:
            return None
        tracked_seconds = float(getattr(tracking_state, "tracked_seconds", 0.0) or 0.0)
        started_at = getattr(tracking_state, "started_at", None) or datetime.now()
        existing = self.get_open_live_session(file_path)
        if existing is None:
            existing = self.get_open_session(project_id, file_path, source="live")
        if existing and existing.project_id != project_id and existing.id is not None:
            existing = self._update_open_session_fields(
                TimeSession(
                    id=existing.id,
                    project_id=project_id,
                    file_path=existing.file_path,
                    file_alias=existing.file_alias,
                    machine_id=existing.machine_id,
                    source=existing.source,
                    start_time=existing.start_time,
                    hourly_rate=(
                        existing.hourly_rate
                        if existing.rate_overridden
                        else self.resolve_hourly_rate(project_id)
                    ),
                    rate_overridden=existing.rate_overridden,
                    live_duration=existing.live_duration,
                    log_history_duration=existing.log_history_duration,
                    log_current_open_hours=existing.log_current_open_hours,
                    balance_delta_hours=existing.balance_delta_hours,
                )
            )
        session = TimeSession(
            id=existing.id if existing else None,
            project_id=project_id,
            file_path=file_path,
            start_time=existing.start_time if existing else started_at,
            hourly_rate=(
                existing.hourly_rate
                if existing
                else self.resolve_hourly_rate(project_id)
            ),
            rate_overridden=existing.rate_overridden if existing else False,
            live_duration=timedelta(seconds=max(0.0, tracked_seconds)),
            log_history_duration=existing.log_history_duration if existing else timedelta(),
            log_current_open_hours=existing.log_current_open_hours if existing else 0.0,
            balance_delta_hours=existing.balance_delta_hours if existing else 0.0,
            source="live",
        )
        return self.upsert_open_session(session)

    def end_session(self, tracking_state: Any) -> Optional[TimeSession]:
        """Adapter for TrackingService session close events."""
        project_id = str(getattr(tracking_state, "project_id", ""))
        file_path = str(getattr(tracking_state, "file_path", ""))
        if not file_path:
            return None
        open_session = self.get_open_live_session(file_path)
        if open_session is None:
            open_session = self.get_open_session(project_id, file_path, source="live")
        if not open_session or open_session.id is None:
            return None
        return self.close_session(open_session.id, datetime.now().isoformat())

    def save_session(self, tracking_state: Any) -> Optional[TimeSession]:
        return self.update_session_duration(tracking_state, 0.0)

    def upsert_session(self, tracking_state: Any) -> Optional[TimeSession]:
        return self.update_session_duration(tracking_state, 0.0)

    def save_tracking_state(self, tracking_state: Any) -> Optional[TimeSession]:
        return self.update_session_duration(tracking_state, 0.0)

    def autosave(self, tracking_state: Any) -> Optional[TimeSession]:
        return self.update_session_duration(tracking_state, 0.0)

    def upsert_open_session(self, session: TimeSession) -> TimeSession:
        row = session.to_row()
        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT * FROM sessions
                WHERE project_id=?
                  AND file_path=?
                  AND machine_id IS ?
                  AND source IS ?
                  AND end_time IS NULL
                """,
                (
                    row["project_id"],
                    row["file_path"],
                    row["machine_id"],
                    row["source"],
                ),
            ).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE sessions
                    SET file_alias=?, start_time=?, hourly_rate=?, rate_overridden=?, live_duration=?,
                        log_history_duration=?, log_current_open_hours=?,
                        balance_delta_hours=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (
                        row["file_alias"],
                        row["start_time"],
                        row["hourly_rate"],
                        row["rate_overridden"],
                        row["live_duration"],
                        row["log_history_duration"],
                        row["log_current_open_hours"],
                        row["balance_delta_hours"],
                        existing["id"],
                    ),
                )
                target_id = int(existing["id"])
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO sessions(
                        project_id, file_path, file_alias, machine_id, source,
                        start_time, end_time, hourly_rate, rate_overridden, live_duration,
                        log_history_duration, log_current_open_hours, balance_delta_hours
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["project_id"],
                        row["file_path"],
                        row["file_alias"],
                        row["machine_id"],
                        row["source"],
                        row["start_time"],
                        row["end_time"],
                        row["hourly_rate"],
                        row["rate_overridden"],
                        row["live_duration"],
                        row["log_history_duration"],
                        row["log_current_open_hours"],
                        row["balance_delta_hours"],
                    ),
                )
                target_id = cursor.lastrowid

            current = conn.execute(
                "SELECT * FROM sessions WHERE id=?",
                (target_id,),
            ).fetchone()
        return TimeSession.from_row(current)

    def get_open_session(
        self,
        project_id: str,
        file_path: str,
        machine_id: str | None = None,
        source: str | None = None,
    ) -> Optional[TimeSession]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM sessions
                WHERE project_id=?
                  AND file_path=?
                  AND machine_id IS ?
                  AND source IS ?
                  AND end_time IS NULL
                ORDER BY id DESC
                LIMIT 1
                """,
                (project_id, file_path, machine_id, source),
            ).fetchone()
        return TimeSession.from_row(row) if row else None

    def close_session(self, session_id: int, end_time: str) -> Optional[TimeSession]:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET end_time=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (end_time, session_id),
            )
            row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return TimeSession.from_row(row) if row else None

    def list_sessions(
        self,
        project_id: str | None = None,
        include_open: bool = True,
        limit: int = 500,
    ) -> list[TimeSession]:
        return self._sessions.list_sessions(
            project_id=project_id,
            include_open=include_open,
            limit=limit,
        )

    def get_session(self, session_id: int) -> Optional[TimeSession]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return TimeSession.from_row(row) if row else None

    def update_session(self, session: TimeSession) -> TimeSession:
        if session.id is None:
            raise ValueError("session.id is required for update")
        if self.is_project_locked(session.project_id):
            raise PermissionError(f"Project '{session.project_id}' is locked for billing")

        existing = self.get_session(session.id)
        if not existing:
            raise ValueError(f"Session not found: {session.id}")

        row = session.to_row()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET project_id=?, file_path=?, file_alias=?, machine_id=?, source=?,
                    start_time=?, end_time=?, hourly_rate=?, rate_overridden=?, live_duration=?,
                    log_history_duration=?, log_current_open_hours=?,
                    balance_delta_hours=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    row["project_id"],
                    row["file_path"],
                    row["file_alias"],
                    row["machine_id"],
                    row["source"],
                    row["start_time"],
                    row["end_time"],
                    row["hourly_rate"],
                    row["rate_overridden"],
                    row["live_duration"],
                    row["log_history_duration"],
                    row["log_current_open_hours"],
                    row["balance_delta_hours"],
                    session.id,
                ),
            )
            current = conn.execute("SELECT * FROM sessions WHERE id=?", (session.id,)).fetchone()

        updated = TimeSession.from_row(current)
        self.add_session_audit(
            session_id=session.id,
            action="update",
            old_values=existing.to_dict(),
            new_values=updated.to_dict(),
            source=session.source,
        )
        return updated

    def delete_session(self, session_id: int) -> None:
        existing = self.get_session(session_id)
        if not existing:
            return
        if self.is_project_locked(existing.project_id):
            raise PermissionError(f"Project '{existing.project_id}' is locked for billing")
        with self._connect() as conn:
            self.add_session_audit(
                session_id=session_id,
                action="delete",
                old_values=existing.to_dict(),
                new_values=None,
                source=existing.source,
            )
            conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))

    def add_exclusion(
        self,
        file_alias: str,
        start_time: str,
        end_time: str | None = None,
        machine_id: str | None = None,
        log_key: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO session_exclusions(
                    file_alias, start_time, end_time, machine_id, log_key, reason
                )
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (file_alias, start_time, end_time, machine_id, log_key, reason),
            )
            row = conn.execute(
                "SELECT * FROM session_exclusions WHERE id=?",
                (cursor.lastrowid,),
            ).fetchone()
        return dict(row) if row else {}

    def list_exclusions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM session_exclusions ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_exclusion(self, exclusion_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM session_exclusions WHERE id=?", (exclusion_id,))

    def add_adjustment(
        self,
        project_id: str,
        file_path: str,
        start_time: str,
        end_time: str,
        hourly_rate: float,
        machine_id: str | None = None,
        notes: str | None = None,
        replaces_log_key: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO session_adjustments(
                    project_id, file_path, start_time, end_time, hourly_rate,
                    machine_id, notes, replaces_log_key
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    file_path,
                    start_time,
                    end_time,
                    hourly_rate,
                    machine_id,
                    notes,
                    replaces_log_key,
                ),
            )
            row = conn.execute(
                "SELECT * FROM session_adjustments WHERE id=?",
                (cursor.lastrowid,),
            ).fetchone()
        return dict(row) if row else {}

    def list_adjustments(self, project_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM session_adjustments"
        params: list[Any] = []
        if project_id:
            query += " WHERE project_id=?"
            params.append(project_id)
        query += " ORDER BY start_time DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def update_adjustment(
        self,
        adjustment_id: int,
        project_id: str,
        file_path: str,
        start_time: str,
        end_time: str,
        hourly_rate: float,
        machine_id: str | None = None,
        notes: str | None = None,
        replaces_log_key: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE session_adjustments
                SET project_id=?, file_path=?, start_time=?, end_time=?, hourly_rate=?,
                    machine_id=?, notes=?, replaces_log_key=?
                WHERE id=?
                """,
                (
                    project_id,
                    file_path,
                    start_time,
                    end_time,
                    hourly_rate,
                    machine_id,
                    notes,
                    replaces_log_key,
                    adjustment_id,
                ),
            )
            row = conn.execute(
                "SELECT * FROM session_adjustments WHERE id=?",
                (adjustment_id,),
            ).fetchone()
        return dict(row) if row else {}

    def delete_adjustment(self, adjustment_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM session_adjustments WHERE id=?", (adjustment_id,))

    def set_conflict_resolution(self, log_key: str, resolution: str) -> None:
        self.set_setting(f"conflict_resolutions:{log_key}", resolution)

    def get_conflict_resolution(self, log_key: str) -> str | None:
        return self.get_setting(f"conflict_resolutions:{log_key}")

    # App settings
    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO app_settings(key, value, updated_at)
                VALUES(?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at
                """,
                (key, value),
            )

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key=?",
                (key,),
            ).fetchone()
        return str(row["value"]) if row else default

    # Log source catalog
    def register_log_source(self, source: str, description: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO log_sources(source, description)
                VALUES(?, ?)
                """,
                (source, description),
            )

    def remove_log_source(self, source: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM log_sources WHERE source=?", (source,))

    def list_log_sources(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM log_sources ORDER BY source COLLATE NOCASE ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    # Session audit
    def add_session_audit(
        self,
        session_id: int,
        action: str,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        source: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO session_audit(session_id, action, old_values, new_values, source)
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    action,
                    json.dumps(old_values) if old_values is not None else None,
                    json.dumps(new_values) if new_values is not None else None,
                    source,
                ),
            )

    def get_session_audit(self, session_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM session_audit
                WHERE session_id=?
                ORDER BY changed_at ASC, id ASC
                """,
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def as_project_id_iter(projects: Iterable[BillableProject]) -> list[str]:
        """Utility helper for callers still keyed by `project_code` strings."""
        return [project.project_code for project in projects]

    def _hourly_rate_for_project(self, project_id: str) -> float:
        return self.resolve_hourly_rate(project_id)
