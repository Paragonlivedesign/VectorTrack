"""Tests for report data builder and report service exports."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from vectortrack.db.repository import Repository
from vectortrack.models import BillableProject, Client, TimeSession
from vectortrack.services.billing_service import BillingContext, BillingService
from vectortrack.services.log_service import LogService
from vectortrack.services.report_data import ReportDataBuilder, ReportFilter
from vectortrack.services.report_service import ReportService
from vectortrack.services.session_aggregator import SessionAggregator, UnifiedSession


@pytest.fixture
def repository(tmp_path):
    db_file = tmp_path / "vectortrack.db"
    legacy_file = tmp_path / "sessions.db"
    return Repository(database_path=db_file, legacy_database_path=legacy_file)


@pytest.fixture
def billing_service():
    return BillingService(rounding_minutes=15, rounding_mode="nearest", after_hours_multiplier=1.25)


@pytest.fixture
def report_builder(repository, billing_service):
    return ReportDataBuilder(
        repository=repository,
        session_aggregator=SessionAggregator(repository),
        billing_service=billing_service,
        log_service=LogService(),
        log_paths=[],
        assigned_files={},
    )


def _seed_project(repository: Repository, code: str = "VT-100", rate: float = 100.0):
    client = repository.create_client(Client(name="ACME Corp"))
    project = repository.create_project(
        BillableProject(
            client_id=client.id or 0,
            project_code=code,
            name="Arena Build",
            hourly_rate=rate,
        )
    )
    return client, project


def test_report_row_dual_amounts_with_rounding(repository, report_builder, billing_service):
    _seed_project(repository)
    start = datetime(2026, 6, 10, 19, 0, 0)
    end = start + timedelta(minutes=20)
    session = UnifiedSession(
        start=start,
        end=end,
        hours=0.3333,
        machine_id="local",
        source="live",
        file_path="I:/arena.vwx",
        file_alias="arena.vwx",
        project_id="VT-100",
        hourly_rate=100.0,
    )
    rows = report_builder.rows_from_unified_sessions([session], "VT-100")
    assert len(rows) == 1
    row = rows[0]
    assert row.raw_hours > 0
    assert row.raw_amount == round(row.raw_hours * 100.0, 2)
    billing = billing_service.compute(
        BillingContext(
            rate=100.0,
            duration_hours=row.raw_hours,
            started_at=start,
        )
    )
    assert row.billed_hours == billing.rounded_hours
    assert row.billed_amount == billing.total_due
    assert row.effective_rate == billing.effective_rate
    assert row.project_name == "Arena Build"
    assert row.project_label == "VT-100 — Arena Build"


def test_report_row_excluded_not_billable(report_builder):
    session = UnifiedSession(
        start=datetime(2026, 6, 10, 10, 0, 0),
        end=datetime(2026, 6, 10, 11, 0, 0),
        hours=1.0,
        machine_id="local",
        source="log",
        file_path="arena.vwx",
        file_alias="arena.vwx",
        project_id="VT-100",
        hourly_rate=75.0,
        is_excluded=True,
    )
    rows = report_builder.rows_from_unified_sessions([session], "VT-100")
    assert rows[0].billable is False
    assert rows[0].billed_amount == 0.0


def test_aggregate_by_project(report_builder):
    sessions = [
        UnifiedSession(
            start=datetime(2026, 6, 10, 10, 0, 0),
            end=datetime(2026, 6, 10, 11, 0, 0),
            hours=1.0,
            machine_id="local",
            source="live",
            file_path="a.vwx",
            file_alias="a.vwx",
            project_id="VT-100",
            hourly_rate=80.0,
        ),
        UnifiedSession(
            start=datetime(2026, 6, 11, 10, 0, 0),
            end=datetime(2026, 6, 11, 11, 30, 0),
            hours=1.5,
            machine_id="local",
            source="live",
            file_path="b.vwx",
            file_alias="b.vwx",
            project_id="VT-100",
            hourly_rate=80.0,
        ),
    ]
    from vectortrack.services.report_data import ReportDataSet

    rows = report_builder.rows_from_unified_sessions(sessions, "VT-100")
    data = ReportDataSet(rows=rows)
    aggregates = data.aggregate_by_project()
    assert len(aggregates) == 1
    assert aggregates[0].raw_hours == 2.5
    assert aggregates[0].billed_amount > 0


def test_build_filters_by_date(repository, report_builder):
    _seed_project(repository)
    inside = TimeSession(
        project_id="VT-100",
        file_path="I:/inside.vwx",
        start_time=datetime(2026, 6, 15, 10, 0, 0),
        end_time=datetime(2026, 6, 15, 11, 0, 0),
        hourly_rate=100.0,
        live_duration=timedelta(hours=1),
        source="manual",
    )
    outside = TimeSession(
        project_id="VT-100",
        file_path="I:/outside.vwx",
        start_time=datetime(2026, 5, 1, 10, 0, 0),
        end_time=datetime(2026, 5, 1, 11, 0, 0),
        hourly_rate=100.0,
        live_duration=timedelta(hours=1),
        source="manual",
    )
    repository.add_manual_session(inside)
    repository.add_manual_session(outside)

    data = report_builder.build(
        ReportFilter(
            from_dt=datetime(2026, 6, 1),
            to_dt=datetime(2026, 6, 30, 23, 59, 59),
            project_code="VT-100",
        )
    )
    assert len(data.active_rows) == 1
    assert data.active_rows[0].file.endswith("inside.vwx")
    assert "VT-100 — Arena Build" in data.filter_summary


def test_csv_row_mapping_uses_client_name(repository, report_builder):
    _seed_project(repository)
    session = UnifiedSession(
        start=datetime(2026, 6, 10, 10, 0, 0),
        end=datetime(2026, 6, 10, 11, 0, 0),
        hours=1.0,
        machine_id="local",
        source="live",
        file_path="arena.vwx",
        file_alias="arena.vwx",
        project_id="VT-100",
        hourly_rate=75.0,
    )
    rows = report_builder.rows_from_unified_sessions([session], "VT-100")
    row = rows[0]
    qb = row.to_qb_csv()
    assert qb["customer"] == "ACME Corp"
    assert qb["project"] == "VT-100 — Arena Build"
    assert qb["description"].startswith("VT-100 — Arena Build — ")
    accountant = row.to_accountant_csv()
    assert accountant["client"] == "ACME Corp"
    assert accountant["project"] == "VT-100 — Arena Build"
    assert accountant["taxable"] == "yes"
    standard = row.to_standard_csv()
    assert standard["project_name"] == "Arena Build"
    assert standard["project"] == "VT-100"


def test_report_service_pdf_and_csv_smoke(tmp_path, repository, report_builder):
    pytest.importorskip("reportlab")
    _seed_project(repository)
    sessions = [
        UnifiedSession(
            start=datetime(2026, 6, 10, 10, 0, 0),
            end=datetime(2026, 6, 10, 11, 0, 0),
            hours=2.0,
            machine_id="local",
            source="live",
            file_path="arena.vwx",
            file_alias="arena.vwx",
            project_id="VT-100",
            hourly_rate=90.0,
        ),
    ]
    rows = report_builder.rows_from_unified_sessions(sessions, "VT-100")

    from vectortrack.services.report_data import ReportDataSet

    data = ReportDataSet(
        rows=rows,
        filter_summary="June 2026",
        from_dt=datetime(2026, 6, 1),
        to_dt=datetime(2026, 6, 30),
    )
    aggregates = data.aggregate_by_project()
    assert aggregates[0].project_label == "VT-100 — Arena Build"
    service = ReportService(output_dir=str(tmp_path))

    master_pdf = service.create_master_pdf(data, aggregates, output_path=str(tmp_path / "master.pdf"))
    project_pdf = service.create_project_pdf(
        data,
        project_name="VT-100 — Arena Build",
        client_name="ACME Corp",
        hourly_rate=90.0,
        output_path=str(tmp_path / "project.pdf"),
    )
    statement_pdf = service.create_client_statement(
        client_name="ACME Corp",
        aggregates=aggregates,
        data=data,
        output_path=str(tmp_path / "statement.pdf"),
    )
    csv_path = service.export_csv(rows, variant="standard", output_path=str(tmp_path / "export.csv"))

    assert Path(master_pdf).exists() and Path(master_pdf).stat().st_size > 0
    assert Path(project_pdf).exists() and Path(project_pdf).stat().st_size > 0
    assert Path(statement_pdf).exists() and Path(statement_pdf).stat().st_size > 0
    assert Path(csv_path).exists()
    content = Path(csv_path).read_text(encoding="utf-8")
    assert "client_name" in content
    assert "billed_amount" in content


def test_clipboard_summary_totals(report_builder):
    from vectortrack.services.report_data import ProjectAggregate

    aggregates = [
        ProjectAggregate(
            project_code="VT-100",
            project_name="Arena",
            project_label="VT-100 — Arena",
            client_name="ACME",
            raw_hours=2.0,
            billed_hours=2.0,
            raw_amount=150.0,
            billed_amount=175.0,
        ),
    ]
    service = ReportService()
    summary = service.build_clipboard_summary(aggregates)
    assert "VT-100 — Arena" in summary
    assert "150.00" in summary
    assert "175.00" in summary
    assert "TOTAL" in summary
