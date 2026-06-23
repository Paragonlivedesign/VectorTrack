"""Tests for orphan project registration."""

from __future__ import annotations

from pathlib import Path

import pytest

from vectortrack.db.repository import Repository
from vectortrack.services.project_sync import sync_orphan_project_codes


@pytest.fixture
def repository(tmp_path):
    db_file = tmp_path / "vectortrack.db"
    legacy_file = tmp_path / "sessions.db"
    return Repository(database_path=db_file, legacy_database_path=legacy_file)


def test_sync_orphan_project_codes_creates_missing_projects(repository: Repository):
    created = sync_orphan_project_codes(
        repository,
        ["62026", "VT-100"],
        default_rate=75.0,
    )
    assert created == ["62026", "VT-100"]
    project = repository.get_project_by_code("62026")
    assert project is not None
    assert project.name == "62026"
    assert project.hourly_rate == 75.0


def test_sync_orphan_project_codes_is_idempotent(repository: Repository):
    sync_orphan_project_codes(repository, ["62026"], default_rate=75.0)
    created = sync_orphan_project_codes(repository, ["62026"], default_rate=75.0)
    assert created == []
    assert len(repository.list_projects(active_only=False)) == 1
