"""Tests for shared clients/projects catalog sync."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from vectortrack.budget import BudgetType, ProjectBudget, load_project_budget, save_project_budget
from vectortrack.db.repository import Repository
from vectortrack.models import BillableProject, Client
from vectortrack.services.catalog_sync import (
    CatalogApplyAction,
    CatalogApplyMode,
    CatalogItemKind,
    CatalogItemStatus,
    CatalogViewRow,
    apply_catalog_rows,
    apply_catalog_to_local,
    build_catalog_view,
    dismiss_suggestion,
    export_local_catalog,
    filter_orphan_project_codes,
    import_remote_project,
    is_suggestion_dismissed,
    merge_catalogs,
    pull_catalog,
    push_catalog,
    sync_catalog,
)
from vectortrack.services.project_sync import sync_orphan_project_codes
from vectortrack.sync_folder import CATALOG_FILENAME


@pytest.fixture
def repository(tmp_path):
    db_file = tmp_path / "vectortrack.db"
    legacy_file = tmp_path / "sessions.db"
    return Repository(database_path=db_file, legacy_database_path=legacy_file)


def _write_catalog(sync_folder: Path, payload: dict) -> None:
    sync_folder.mkdir(parents=True, exist_ok=True)
    (sync_folder / CATALOG_FILENAME).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_export_import_roundtrip_preserves_projects(repository: Repository):
    client = repository.create_client(Client(name="Acme Corp", code="ACME"))
    repository.create_project(
        BillableProject(
            client_id=client.id or 0,
            project_code="62026",
            name="Main Street",
            hourly_rate=150.0,
        )
    )
    save_project_budget(repository, "62026", ProjectBudget(BudgetType.HOURS, 40.0))

    exported = export_local_catalog(repository)
    empty_repo = Repository(
        database_path=repository.database_path.parent / "other.db",
        legacy_database_path=repository.legacy_database_path.parent / "other-sessions.db",
    )
    summary = apply_catalog_to_local(empty_repo, exported)

    assert summary.clients_added == 1
    assert summary.projects_added == 1
    project = empty_repo.get_project_by_code("62026")
    assert project is not None
    assert project.name == "Main Street"
    assert project.hourly_rate == 150.0
    budget = load_project_budget(empty_repo, "62026")
    assert budget == ProjectBudget(BudgetType.HOURS, 40.0)


def test_build_catalog_view_remote_only_and_in_sync(repository: Repository):
    client = repository.create_client(Client(name="Acme Corp", code="ACME"))
    repository.create_project(
        BillableProject(
            client_id=client.id or 0,
            project_code="62026",
            name="Main Street",
            hourly_rate=150.0,
        )
    )
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    catalog = {
        "version": 1,
        "updated_at": ts,
        "clients": {
            "ACME": {
                "name": "Acme Corp",
                "code": "ACME",
                "is_active": True,
                "updated_at": ts,
            }
        },
        "projects": {
            "62026": {
                "client_key": "ACME",
                "project_code": "62026",
                "name": "Main Street",
                "hourly_rate": 150.0,
                "is_active": True,
                "is_locked": False,
                "locked_at": None,
                "invoice_number": None,
                "budget": {"type": "none", "amount": 0.0},
                "aliases": [],
                "updated_at": ts,
            },
            "REMOTE01": {
                "client_key": "ACME",
                "project_code": "REMOTE01",
                "name": "Remote Project",
                "hourly_rate": 200.0,
                "is_active": True,
                "is_locked": False,
                "locked_at": None,
                "invoice_number": None,
                "budget": {"type": "none", "amount": 0.0},
                "aliases": [],
                "updated_at": ts,
            },
        },
    }
    diff = build_catalog_view(repository, catalog)
    statuses = {(row.key, row.status) for row in diff.rows if row.kind == CatalogItemKind.PROJECT}
    assert ("62026", CatalogItemStatus.IN_SYNC) in statuses
    assert ("REMOTE01", CatalogItemStatus.REMOTE_ONLY) in statuses
    assert diff.remote_only_count >= 1


def test_build_catalog_view_conflict(repository: Repository):
    client = repository.create_client(Client(name="Acme Corp", code="ACME"))
    repository.create_project(
        BillableProject(
            client_id=client.id or 0,
            project_code="62026",
            name="Local Name",
            hourly_rate=100.0,
        )
    )
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    catalog = export_local_catalog(repository)
    catalog["projects"]["62026"]["name"] = "Remote Name"
    catalog["projects"]["62026"]["hourly_rate"] = 175.0

    diff = build_catalog_view(repository, catalog)
    conflict = next(
        row
        for row in diff.rows
        if row.kind == CatalogItemKind.PROJECT and row.key == "62026"
    )
    assert conflict.status == CatalogItemStatus.CONFLICT
    assert "name" in conflict.field_diffs


def test_fuzzy_client_is_suggestion_not_auto_applied(repository: Repository):
    repository.create_client(Client(name="Acme Corp", code="ACME"))
    newer = datetime.now(timezone.utc).isoformat(timespec="seconds")
    catalog = {
        "version": 1,
        "updated_at": newer,
        "clients": {
            "ACME2": {
                "name": "ACME Corp",
                "code": "ACME2",
                "is_active": True,
                "updated_at": newer,
            }
        },
        "projects": {},
    }
    diff = build_catalog_view(repository, catalog)
    assert len(repository.list_clients(active_only=False)) == 1
    suggestions = [
        row
        for row in diff.rows
        if row.status == CatalogItemStatus.SUGGESTED_DUPLICATE
    ]
    assert len(suggestions) == 1

    summary = apply_catalog_to_local(repository, catalog, fuzzy_merge=False)
    assert summary.fuzzy_merged == []
    assert summary.clients_added == 1
    assert len(repository.list_clients(active_only=False)) == 2


def test_apply_catalog_rows_import_and_merge(repository: Repository):
    repository.create_client(Client(name="Acme Corp", code="ACME"))
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    catalog = {
        "version": 1,
        "updated_at": ts,
        "clients": {
            "ACME2": {
                "name": "ACME Corp",
                "code": "ACME2",
                "is_active": True,
                "updated_at": ts,
            }
        },
        "projects": {
            "REMOTE01": {
                "client_key": "ACME2",
                "project_code": "REMOTE01",
                "name": "Remote Project",
                "hourly_rate": 200.0,
                "is_active": True,
                "is_locked": False,
                "locked_at": None,
                "invoice_number": None,
                "budget": {"type": "none", "amount": 0.0},
                "aliases": [],
                "updated_at": ts,
            },
        },
    }
    diff = build_catalog_view(repository, catalog)
    remote_row = next(
        row for row in diff.rows if row.key == "REMOTE01" and row.kind == CatalogItemKind.PROJECT
    )
    summary = apply_catalog_rows(
        repository,
        catalog,
        [CatalogApplyAction(row=remote_row, mode=CatalogApplyMode.IMPORT_REMOTE)],
    )
    assert summary.projects_added == 1
    project = repository.get_project_by_code("REMOTE01")
    assert project is not None
    assert project.name == "Remote Project"

    suggestion = next(
        row for row in diff.rows if row.status == CatalogItemStatus.SUGGESTED_DUPLICATE
    )
    merge_summary = apply_catalog_rows(
        repository,
        catalog,
        [CatalogApplyAction(row=suggestion, mode=CatalogApplyMode.MERGE_CLIENT)],
    )
    assert merge_summary.clients_updated == 1


def test_apply_catalog_rows_keep_local(repository: Repository):
    client = repository.create_client(Client(name="Acme Corp", code="ACME"))
    repository.create_project(
        BillableProject(
            client_id=client.id or 0,
            project_code="62026",
            name="Local Name",
            hourly_rate=100.0,
        )
    )
    ts = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(timespec="seconds")
    catalog = {
        "version": 1,
        "updated_at": ts,
        "clients": {
            "ACME": {
                "name": "Acme Corp",
                "code": "ACME",
                "is_active": True,
                "updated_at": ts,
            }
        },
        "projects": {
            "62026": {
                "client_key": "ACME",
                "project_code": "62026",
                "name": "Remote Name",
                "hourly_rate": 175.0,
                "is_active": True,
                "is_locked": False,
                "locked_at": None,
                "invoice_number": None,
                "budget": {"type": "none", "amount": 0.0},
                "aliases": [],
                "updated_at": ts,
            }
        },
    }
    diff = build_catalog_view(repository, catalog)
    conflict = next(row for row in diff.rows if row.key == "62026")
    summary = apply_catalog_rows(
        repository,
        catalog,
        [CatalogApplyAction(row=conflict, mode=CatalogApplyMode.KEEP_LOCAL)],
    )
    assert summary.projects_updated == 0
    project = repository.get_project_by_code("62026")
    assert project is not None
    assert project.name == "Local Name"


def test_dismissed_suggestion_hidden_until_remote_changes(repository: Repository):
    repository.create_client(Client(name="Acme Corp", code="ACME"))
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    catalog = {
        "version": 1,
        "updated_at": ts,
        "clients": {
            "ACME2": {
                "name": "ACME Corp",
                "code": "ACME2",
                "is_active": True,
                "updated_at": ts,
            }
        },
        "projects": {},
    }
    dismiss_suggestion(repository, "client", "ACME2", "ACME", ts)
    assert is_suggestion_dismissed(repository, "client", "ACME2", "ACME", ts)
    diff = build_catalog_view(repository, catalog)
    assert not any(row.status == CatalogItemStatus.SUGGESTED_DUPLICATE for row in diff.rows)

    newer = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(timespec="seconds")
    catalog["clients"]["ACME2"]["updated_at"] = newer
    diff = build_catalog_view(repository, catalog)
    assert any(row.status == CatalogItemStatus.SUGGESTED_DUPLICATE for row in diff.rows)


def test_merge_catalogs_local_wins_on_tie():
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    local = {
        "version": 1,
        "updated_at": ts,
        "clients": {},
        "projects": {
            "62026": {
                "client_key": "ACME",
                "project_code": "62026",
                "name": "Local Name",
                "hourly_rate": 120.0,
                "updated_at": ts,
            }
        },
    }
    remote = {
        "version": 1,
        "updated_at": ts,
        "clients": {},
        "projects": {
            "62026": {
                "client_key": "ACME",
                "project_code": "62026",
                "name": "Remote Name",
                "hourly_rate": 90.0,
                "updated_at": ts,
            }
        },
    }
    merged = merge_catalogs(local, remote, local_wins_tie=True)
    assert merged["projects"]["62026"]["name"] == "Local Name"


def test_sync_push_only_does_not_modify_local_db(repository: Repository, tmp_path):
    before = len(repository.list_clients(active_only=False))
    sync_folder = tmp_path / "sync"
    newer = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _write_catalog(
        sync_folder,
        {
            "version": 1,
            "updated_at": newer,
            "clients": {
                "REMOTE": {
                    "name": "Remote Client",
                    "code": "REMOTE",
                    "is_active": True,
                    "updated_at": newer,
                }
            },
            "projects": {},
        },
    )
    summary, ok, err = sync_catalog(str(sync_folder), repository)
    assert summary is None
    assert ok
    assert not err
    assert len(repository.list_clients(active_only=False)) == before


def test_push_and_pull_catalog_explicit(repository: Repository, tmp_path):
    sync_folder = tmp_path / "sync"
    client = repository.create_client(Client(name="Acme Corp", code="ACME"))
    repository.create_project(
        BillableProject(
            client_id=client.id or 0,
            project_code="62026",
            name="Main Street",
            hourly_rate=150.0,
        )
    )

    ok, err = push_catalog(str(sync_folder), repository)
    assert ok, err
    assert (sync_folder / CATALOG_FILENAME).is_file()

    other_repo = Repository(
        database_path=tmp_path / "remote.db",
        legacy_database_path=tmp_path / "remote-sessions.db",
    )
    summary = pull_catalog(str(sync_folder), other_repo)
    assert summary is not None
    assert summary.projects_added == 1
    assert other_repo.get_project_by_code("62026") is not None


def test_orphan_code_in_catalog_skips_stub(repository: Repository, tmp_path):
    sync_folder = tmp_path / "sync"
    newer = datetime.now(timezone.utc).isoformat(timespec="seconds")
    catalog = {
        "version": 1,
        "updated_at": newer,
        "clients": {
            "ACME": {
                "name": "Acme Corp",
                "code": "ACME",
                "is_active": True,
                "updated_at": newer,
            }
        },
        "projects": {
            "REMOTE01": {
                "client_key": "ACME",
                "project_code": "REMOTE01",
                "name": "Remote Project",
                "hourly_rate": 200.0,
                "is_active": True,
                "is_locked": False,
                "locked_at": None,
                "invoice_number": None,
                "budget": {"type": "none", "amount": 0.0},
                "aliases": [],
                "updated_at": newer,
            }
        },
    }
    _write_catalog(sync_folder, catalog)

    stub_codes, catalog_only = filter_orphan_project_codes(["REMOTE01", "BRANDNEW"], catalog)
    assert stub_codes == ["BRANDNEW"]
    assert catalog_only == ["REMOTE01"]

    created = sync_orphan_project_codes(repository, stub_codes, default_rate=75.0)
    assert created == ["BRANDNEW"]
    assert repository.get_project_by_code("REMOTE01") is None

    summary = import_remote_project(repository, catalog, "REMOTE01")
    assert summary.projects_added == 1
    project = repository.get_project_by_code("REMOTE01")
    assert project is not None
    assert project.name == "Remote Project"
