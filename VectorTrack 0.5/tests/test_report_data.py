"""Tests for report_data builder."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from vectortrack.db.repository import Repository
from vectortrack.models import TimeSession
from vectortrack.services.billing_service import BillingService
from vectortrack.services.log_service import LogService
from vectortrack.services.report_data import ReportDataBuilder, ReportFilter
from vectortrack.services.session_aggregator import SessionAggregator


@pytest.fixture
def repository(tmp_path):
    return Repository(database_path=tmp_path / "vectortrack.db")


def test_report_data_builder_filters_by_date(repository: Repository) -> None:
    start = datetime.now() - timedelta(days=2)
    session = TimeSession(
        project_id="PRJ-1",
        file_path="I:/job/file.vwx",
        start_time=start,
        end_time=start + timedelta(hours=1),
        hourly_rate=100.0,
        source="manual",
    )
    repository.add_manual_session(session)

    builder = ReportDataBuilder(
        repository=repository,
        billing_service=BillingService(),
        session_aggregator=SessionAggregator(repository),
        log_service=LogService(),
        log_paths=[],
        assigned_files={},
    )
    dataset = builder.build(
        ReportFilter(
            from_dt=datetime.now() - timedelta(days=3),
            to_dt=datetime.now(),
        )
    )
    assert len(dataset.rows) >= 1
