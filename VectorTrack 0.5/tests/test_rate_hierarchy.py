"""Tests for session rate hierarchy and project assignment strategies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from vectortrack.db.repository import Repository
from vectortrack.models import BillableProject, Client, TimeSession


@pytest.fixture
def repository(tmp_path):
    db_file = tmp_path / "rates.db"
    legacy_file = tmp_path / "legacy.db"
    return Repository(
        database_path=db_file,
        legacy_database_path=legacy_file,
        default_hourly_rate=80.0,
    )


def _tracking_state(
    file_path: str,
    project_id: str = "",
    tracked_seconds: float = 3600.0,
) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        project_id=project_id,
        file_path=file_path,
        started_at=now,
        tracked_seconds=tracked_seconds,
    )


def test_unassigned_start_session_uses_default_rate(repository: Repository):
    state = _tracking_state("I:/draft/unassigned.vwx")
    session = repository.start_session(state)
    assert session.project_id == ""
    assert session.hourly_rate == 80.0
    assert session.end_time is None


def test_unassigned_update_session_duration_persists(repository: Repository):
    state = _tracking_state("I:/draft/unassigned.vwx", tracked_seconds=1800.0)
    repository.start_session(state)
    state.tracked_seconds = 5400.0
    updated = repository.update_session_duration(state, 3600.0)
    assert updated is not None
    assert updated.hourly_rate == 80.0
    assert updated.live_duration == timedelta(seconds=5400.0)


def test_assign_file_project_rate_migrates_open_session(repository: Repository):
    client = repository.create_client(Client(name="Acme", code="AC"))
    project = repository.create_project(
        BillableProject(
            client_id=client.id or 0,
            project_code="P-100",
            name="Project 100",
            hourly_rate=125.0,
        )
    )
    assert project.id is not None

    state = _tracking_state("I:/draft/site.vwx", tracked_seconds=7200.0)
    repository.start_session(state)

    migrated, split = repository.assign_file_to_project(
        "I:/draft/site.vwx",
        "P-100",
        rate_strategy=Repository.RATE_STRATEGY_PROJECT,
    )
    assert split is False
    assert migrated is not None
    assert migrated.project_id == "P-100"
    assert migrated.hourly_rate == 125.0
    assert migrated.rate_overridden is False
    assert migrated.live_duration == timedelta(seconds=7200.0)

    open_sessions = repository.list_sessions(project_id="P-100", include_open=True, limit=10)
    assert len([s for s in open_sessions if s.end_time is None]) == 1
    assert repository.get_open_live_session("I:/draft/site.vwx") is not None


def test_assign_file_keep_rate_preserves_hourly_rate(repository: Repository):
    client = repository.create_client(Client(name="Acme", code="AC"))
    repository.create_project(
        BillableProject(
            client_id=client.id or 0,
            project_code="P-200",
            name="Project 200",
            hourly_rate=150.0,
        )
    )

    state = _tracking_state("I:/draft/keep.vwx", tracked_seconds=3600.0)
    repository.start_session(state)

    migrated, split = repository.assign_file_to_project(
        "I:/draft/keep.vwx",
        "P-200",
        rate_strategy=Repository.RATE_STRATEGY_KEEP,
    )
    assert split is False
    assert migrated is not None
    assert migrated.project_id == "P-200"
    assert migrated.hourly_rate == 80.0
    assert migrated.rate_overridden is True


def test_assign_file_split_closes_and_opens_new_session(repository: Repository):
    client = repository.create_client(Client(name="Acme", code="AC"))
    repository.create_project(
        BillableProject(
            client_id=client.id or 0,
            project_code="P-300",
            name="Project 300",
            hourly_rate=110.0,
        )
    )

    state = _tracking_state("I:/draft/split.vwx", tracked_seconds=5400.0)
    started = repository.start_session(state)
    assert started.id is not None

    new_open, split = repository.assign_file_to_project(
        "I:/draft/split.vwx",
        "P-300",
        rate_strategy=Repository.RATE_STRATEGY_SPLIT,
    )
    assert split is True
    assert new_open is not None
    assert new_open.project_id == "P-300"
    assert new_open.hourly_rate == 110.0
    assert new_open.live_duration == timedelta()

    closed = repository.get_session(started.id)
    assert closed is not None
    assert closed.end_time is not None
    assert closed.hourly_rate == 80.0


def test_set_open_session_rate_marks_override(repository: Repository):
    state = _tracking_state("I:/draft/custom.vwx", tracked_seconds=1800.0)
    repository.start_session(state)

    updated = repository.set_open_session_rate("I:/draft/custom.vwx", 200.0)
    assert updated is not None
    assert updated.hourly_rate == 200.0
    assert updated.rate_overridden is True


def test_resolve_hourly_rate_for_empty_project_uses_default(repository: Repository):
    assert repository.resolve_hourly_rate("") == 80.0


def test_end_unassigned_session(repository: Repository):
    state = _tracking_state("I:/draft/close.vwx", tracked_seconds=900.0)
    repository.start_session(state)
    closed = repository.end_session(state)
    assert closed is not None
    assert closed.end_time is not None
    assert closed.hourly_rate == 80.0
