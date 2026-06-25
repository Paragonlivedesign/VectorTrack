"""Tests for merged report rows across multiple machines."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from vectortrack.db.repository import Repository
from vectortrack.models import BillableProject, Client
from vectortrack.services.billing_service import BillingService
from vectortrack.services.log_service import LogService
from vectortrack.services.report_data import ReportDataBuilder, ReportFilter
from vectortrack.services.session_aggregator import SessionAggregator
from vectortrack.sync_config import SyncConfig
from vectortrack.sync_folder import gather_sync_log_paths

CLOSED_LOG = """
Opened "Arena.vwx" at 6/1/2025 9:00:00 AM
Closed "Arena.vwx" at 6/1/2025 11:00:00 AM
"""


def _write_log(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_report_builder_includes_remote_machine_logs(tmp_path):
    db_file = tmp_path / "vectortrack.db"
    repository = Repository(database_path=db_file, legacy_database_path=tmp_path / "sessions.db")
    client = repository.create_client(Client(name="ACME"))
    repository.create_project(
        BillableProject(
            client_id=client.id or 0,
            project_code="Arena",
            name="Arena",
            hourly_rate=100.0,
        )
    )

    sync_folder = tmp_path / "sync"
    local_log = _write_log(tmp_path / "local" / "2026" / "Vectorworks Log.txt", CLOSED_LOG)
    remote_log = _write_log(
        sync_folder / "machines" / "remote-machine" / "2026" / "Vectorworks Log.txt",
        CLOSED_LOG,
    )

    config = SyncConfig(enabled=True, folder=str(sync_folder), machine_id="local-machine")
    paths, machine_count = gather_sync_log_paths([local_log], config, 2026)
    assert remote_log in paths
    assert machine_count == 2

    builder = ReportDataBuilder(
        repository=repository,
        session_aggregator=SessionAggregator(repository),
        billing_service=BillingService(),
        log_service=LogService(),
        log_paths=paths,
        assigned_files={"Arena.vwx": "Arena"},
    )
    dataset = builder.build(
        ReportFilter(
            from_dt=datetime(2025, 1, 1),
            to_dt=datetime(2025, 12, 31, 23, 59, 59),
            project_code="Arena",
        )
    )
    log_rows = [row for row in dataset.rows if row.source == "log"]
    machine_ids = {row.machine_id for row in log_rows}
    assert "remote-machine" in machine_ids
    assert len(log_rows) >= 2
