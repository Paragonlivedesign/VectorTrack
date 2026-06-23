"""
Tests for v4 repository and schema behavior.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from vectortrack.db.repository import Repository
from vectortrack.models import AliasRule, BillableProject, Client, TimeSession


@pytest.fixture
def repository(tmp_path):
    db_file = tmp_path / "vectortrack.db"
    legacy_file = tmp_path / "sessions.db"
    return Repository(database_path=db_file, legacy_database_path=legacy_file)


def test_client_project_alias_crud(repository: Repository):
    client = repository.create_client(Client(name="ACME", code="ACM"))
    assert client.id is not None

    project = repository.create_project(
        BillableProject(
            client_id=client.id,
            project_code="VT-001",
            name="Headquarters",
            hourly_rate=125.0,
        )
    )
    assert project.id is not None

    alias = repository.upsert_alias_rule(
        AliasRule(project_id=project.id, alias_pattern="hq-main", priority=10)
    )
    assert alias.id is not None

    resolved = repository.resolve_project_by_file_alias("2026-hq-main-01.vwx")
    assert resolved is not None
    assert resolved.project_code == "VT-001"


def test_upsert_open_session_updates_existing(repository: Repository):
    initial = TimeSession(
        project_id="VT-001",
        file_path="I:/projects/hq-main.vwx",
        file_alias="hq-main.vwx",
        machine_id="machine-01",
        source="vectorworks-log",
        start_time=datetime.now(timezone.utc),
        hourly_rate=120.0,
        live_duration=timedelta(minutes=10),
    )
    stored = repository.upsert_open_session(initial)
    assert stored.id is not None

    initial.live_duration += timedelta(minutes=15)
    updated = repository.upsert_open_session(initial)
    assert updated.id == stored.id
    assert updated.live_duration.total_seconds() == 25 * 60


def test_settings_sources_and_audit(repository: Repository):
    repository.set_setting("theme", "dark")
    assert repository.get_setting("theme") == "dark"
    assert repository.get_setting("missing", default="fallback") == "fallback"

    repository.register_log_source("vectorworks-log", "Log parser")
    sources = repository.list_log_sources()
    assert any(row["source"] == "vectorworks-log" for row in sources)

    session = repository.upsert_open_session(
        TimeSession(
            project_id="VT-002",
            file_path="I:/projects/phase2.vwx",
            machine_id="machine-02",
            source="vectorworks-log",
            start_time=datetime.now(timezone.utc),
        )
    )
    repository.add_session_audit(
        session_id=session.id,
        action="updated",
        old_values={"live_duration": 0},
        new_values={"live_duration": 120},
        source="test",
    )
    audit_rows = repository.get_session_audit(session.id)
    assert len(audit_rows) == 1
    assert audit_rows[0]["action"] == "updated"


def test_v1_sessions_db_migration(tmp_path):
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
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                "LEG-001",
                "I:/legacy/old-file.vwx",
                datetime.now(timezone.utc).isoformat(),
                None,
                3600.0,
                95.0,
            ),
        )

    repo = Repository(
        database_path=tmp_path / "vectortrack.db",
        legacy_database_path=legacy_db,
    )
    sessions = repo.list_sessions(project_id="LEG-001", include_open=True)
    assert len(sessions) == 1
    assert sessions[0].source == "legacy-v1"
    assert sessions[0].live_duration.total_seconds() == 3600.0


def test_project_lock_blocks_manual_entry(repository: Repository):
    client = repository.create_client(Client(name="LockCo", code="LC"))
    project = repository.create_project(
        BillableProject(
            client_id=client.id or 0,
            project_code="LOCK-1",
            name="Locked Job",
            hourly_rate=100.0,
        )
    )
    assert project.id is not None
    repository.set_project_lock("LOCK-1", locked=True, invoice_number="INV-100")

    session = TimeSession(
        project_id="LOCK-1",
        file_path="I:/projects/locked.vwx",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        hourly_rate=100.0,
        live_duration=timedelta(hours=1),
        source="manual",
    )
    with pytest.raises(PermissionError):
        repository.add_manual_session(session)

    repository.set_project_lock("LOCK-1", locked=False)
    saved = repository.add_manual_session(session)
    assert saved.id is not None


def test_repository_write_waits_for_db_lock(repository: Repository):
    lock_conn = sqlite3.connect(str(repository.database_path), timeout=1.0)
    lock_conn.execute("BEGIN EXCLUSIVE")
    lock_conn.execute(
        "INSERT INTO app_settings(key, value, updated_at) VALUES('lock_key', '1', CURRENT_TIMESTAMP)"
    )

    errors: list[Exception] = []

    def delayed_write():
        try:
            repository.set_setting("after_lock", "ok")
        except Exception as exc:  # pragma: no cover - captured assertion path
            errors.append(exc)

    worker = threading.Thread(target=delayed_write)
    worker.start()
    time.sleep(0.2)
    lock_conn.rollback()
    lock_conn.close()
    worker.join(timeout=2.0)

    assert not errors
    assert repository.get_setting("after_lock") == "ok"
