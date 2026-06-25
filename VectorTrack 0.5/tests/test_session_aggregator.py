"""Tests for session aggregation, dedupe, conflicts, and scope filtering."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from vectortrack.db.repository import Repository
from vectortrack.models import AliasRule, BillableProject, Client, TimeSession
from vectortrack.services.session_aggregator import (
    SessionAggregator,
    UnifiedSession,
    make_log_key,
    machine_id_from_log_path,
    normalize_file_name,
)
from vectortrack.services.vw_identity import hostname_hash_machine_id, local_machine_id

CLOSED_LOG = """
Opened "MyProject.vwx" at 6/1/2025 9:00:00 AM
Closed "MyProject.vwx" at 6/1/2025 11:00:00 AM
Opened "MyProject.vwx" at 6/2/2025 1:00:00 PM
Closed "MyProject.vwx" at 6/2/2025 3:00:00 PM
"""

OVERLAP_LOG_A = """
Opened "Shared.vwx" at 6/1/2025 9:00:00 AM
Closed "Shared.vwx" at 6/1/2025 12:00:00 PM
"""

OVERLAP_LOG_B = """
Opened "Shared.vwx" at 6/1/2025 10:00:00 AM
Closed "Shared.vwx" at 6/1/2025 1:00:00 PM
"""

SECOND_FILE_LOG = """
Opened "OtherFile.vwx" at 6/3/2025 9:00:00 AM
Closed "OtherFile.vwx" at 6/3/2025 10:00:00 AM
"""

VERSIONED_LOG = """
Opened "Sample Project v2026.vwx" at 6/10/2025 9:00:00 AM
Saved "Sample Project v2026.vwx" as "Sample Project v2026 v2.vwx".
Closed "Sample Project v2026 v2.vwx" at 6/10/2025 12:00:00 PM
"""


@pytest.fixture
def repository(tmp_path):
    db_file = tmp_path / "vectortrack.db"
    legacy_file = tmp_path / "sessions.db"
    return Repository(database_path=db_file, legacy_database_path=legacy_file)


@pytest.fixture
def aggregator(repository: Repository) -> SessionAggregator:
    return SessionAggregator(repository)


def _write_log(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_normalize_file_name_and_machine_id_from_path():
    assert normalize_file_name(r"C:\Projects\MyProject.vwx") == "myproject"
    sync_path = r"D:/Sync/machines/laptop-a/2025/Vectorworks Log.txt"
    assert machine_id_from_log_path(sync_path) == "laptop-a"
    assert machine_id_from_log_path(r"C:\Nemetschek\2025\Vectorworks Log.txt") == local_machine_id(2025)


def test_merge_log_sessions_from_two_machines(tmp_path, aggregator: SessionAggregator):
    log_a = _write_log(
        tmp_path / "machines" / "machine-a" / "2025" / "Vectorworks Log.txt",
        CLOSED_LOG,
    )
    log_b = _write_log(
        tmp_path / "machines" / "machine-b" / "2025" / "Vectorworks Log.txt",
        CLOSED_LOG,
    )

    sessions = aggregator.sessions_for_file(
        file_path="MyProject.vwx",
        log_paths=[log_a, log_b],
        project_id="MyProject",
    )

    log_sessions = [session for session in sessions if session.source == "log"]
    assert len(log_sessions) == 4
    machines = {session.machine_id for session in log_sessions}
    assert machines == {"machine-a", "machine-b"}


def test_detect_conflicts_on_overlapping_intervals(aggregator: SessionAggregator):
    start_a = datetime(2025, 6, 1, 9, 0, 0)
    end_a = datetime(2025, 6, 1, 12, 0, 0)
    start_b = datetime(2025, 6, 1, 10, 0, 0)
    end_b = datetime(2025, 6, 1, 13, 0, 0)

    left = UnifiedSession(
        start=start_a,
        end=end_a,
        hours=3.0,
        machine_id="machine-a",
        source="log",
        file_path="Shared.vwx",
        file_alias="Shared.vwx",
        project_id="Shared",
        log_key=make_log_key(start_a, end_a, "Shared.vwx", "machine-a"),
    )
    right = UnifiedSession(
        start=start_b,
        end=end_b,
        hours=3.0,
        machine_id="machine-b",
        source="log",
        file_path="Shared.vwx",
        file_alias="Shared.vwx",
        project_id="Shared",
        log_key=make_log_key(start_b, end_b, "Shared.vwx", "machine-b"),
    )

    groups = aggregator.detect_conflicts([left, right])
    assert len(groups) == 1
    assert left.conflict_ids
    assert right.conflict_ids


def test_conflict_detection_from_synced_logs(tmp_path, aggregator: SessionAggregator):
    log_a = _write_log(
        tmp_path / "machines" / "machine-a" / "2025" / "Vectorworks Log.txt",
        OVERLAP_LOG_A,
    )
    log_b = _write_log(
        tmp_path / "machines" / "machine-b" / "2025" / "Vectorworks Log.txt",
        OVERLAP_LOG_B,
    )

    sessions = aggregator.sessions_for_file(
        file_path="Shared.vwx",
        log_paths=[log_a, log_b],
        project_id="Shared",
    )
    conflict_rows = [session for session in sessions if session.status == "Conflict"]
    assert len(conflict_rows) == 2


def test_db_session_suppresses_duplicate_log_session(
    tmp_path,
    repository: Repository,
    aggregator: SessionAggregator,
):
    log_path = _write_log(tmp_path / "local" / "Vectorworks Log.txt", CLOSED_LOG)
    start = datetime(2025, 6, 1, 9, 0, 0)
    end = datetime(2025, 6, 1, 11, 0, 0)

    repository.upsert_open_session(
        TimeSession(
            project_id="MyProject",
            file_path="MyProject.vwx",
            file_alias="MyProject.vwx",
            machine_id="local",
            source="manual",
            start_time=start,
            end_time=end,
            hourly_rate=100.0,
            live_duration=timedelta(hours=2),
        )
    )

    sessions = aggregator.sessions_for_file(
        file_path="MyProject.vwx",
        log_paths=[log_path],
        project_id="MyProject",
    )

    log_sessions = [session for session in sessions if session.source == "log" and session.start == start]
    assert not log_sessions
    db_sessions = [session for session in sessions if session.source == "manual"]
    assert len(db_sessions) == 1


def test_project_mode_includes_multiple_files_via_alias(
    tmp_path,
    repository: Repository,
    aggregator: SessionAggregator,
):
    client = repository.create_client(Client(name="ACME", code="ACM"))
    project = repository.create_project(
        BillableProject(
            client_id=client.id,
            project_code="VT-100",
            name="Campus",
            hourly_rate=90.0,
        )
    )
    repository.upsert_alias_rule(
        AliasRule(project_id=project.id, alias_pattern="MyProject.vwx", priority=1)
    )
    repository.upsert_alias_rule(
        AliasRule(project_id=project.id, alias_pattern="OtherFile.vwx", priority=2)
    )

    log_path = _write_log(
        tmp_path / "2025" / "Vectorworks Log.txt",
        CLOSED_LOG + SECOND_FILE_LOG,
    )

    sessions = aggregator.sessions_for_project(
        project_code="VT-100",
        log_paths=[log_path],
    )

    aliases = {session.file_alias.lower() for session in sessions if session.source == "log"}
    assert "myproject.vwx" in aliases
    assert "otherfile.vwx" in aliases


def test_exclusions_mark_log_sessions(aggregator: SessionAggregator, repository: Repository, tmp_path):
    log_path = _write_log(tmp_path / "2025" / "Vectorworks Log.txt", CLOSED_LOG)
    sessions = aggregator.sessions_for_file(
        file_path="MyProject.vwx",
        log_paths=[log_path],
        project_id="MyProject",
    )
    target = next(session for session in sessions if session.source == "log")
    assert target.log_key

    repository.add_exclusion(
        file_alias=target.file_alias,
        start_time=target.start.isoformat(),
        end_time=target.end.isoformat(),
        machine_id=target.machine_id,
        log_key=target.log_key,
        reason="test",
    )

    refreshed = aggregator.sessions_for_file(
        file_path="MyProject.vwx",
        log_paths=[log_path],
        project_id="MyProject",
    )
    excluded = next(session for session in refreshed if session.log_key == target.log_key)
    assert excluded.is_excluded is True
    assert excluded.exclusion_id is not None
    assert excluded.status == "Excluded"


def test_project_mode_finds_log_hours_without_vwx_extension(
    tmp_path,
    aggregator: SessionAggregator,
):
    log_path = _write_log(tmp_path / "2025" / "Vectorworks Log.txt", CLOSED_LOG)
    sessions = aggregator.sessions_for_project(
        project_code="MyProject",
        log_paths=[log_path],
    )
    log_sessions = [session for session in sessions if session.source == "log"]
    assert len(log_sessions) == 2
    assert sum(session.hours for session in log_sessions) == pytest.approx(4.0, abs=0.01)


def test_project_mode_includes_version_two_sibling_file(
    tmp_path,
    aggregator: SessionAggregator,
):
    log_path = _write_log(tmp_path / "2025" / "Vectorworks Log.txt", VERSIONED_LOG)
    now = datetime(2025, 6, 10, 15, 0, 0)
    sessions = aggregator.sessions_for_project(
        project_code="Sample Project v2026",
        log_paths=[log_path],
        now=now,
    )
    aliases = {session.file_alias for session in sessions if session.source == "log"}
    assert len(aliases) >= 1
    log_hours = sum(session.hours for session in sessions if session.source == "log")
    assert log_hours >= 3.0
