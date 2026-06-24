"""Build normalized report rows from merged sessions and billing rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from vectortrack.services.billing_service import BillingContext, BillingService
from vectortrack.services.log_service import LogService
from vectortrack.services.session_aggregator import SessionAggregator, UnifiedSession


def _project_report_label(name: str, code: str = "") -> str:
    cleaned_name = name.strip()
    cleaned_code = code.strip()
    if not cleaned_code or cleaned_code == cleaned_name:
        return cleaned_name or cleaned_code
    if not cleaned_name:
        return cleaned_code
    return f"{cleaned_code} — {cleaned_name}"


@dataclass(frozen=True)
class ReportFilter:
    from_dt: datetime
    to_dt: datetime
    project_code: str = ""
    client_id: int = 0


@dataclass
class ReportRow:
    date: str
    start: datetime
    end: datetime
    project_code: str
    project_name: str
    project_label: str
    client_name: str
    file: str
    source: str
    machine_id: str
    raw_hours: float
    billed_hours: float
    rate: float
    effective_rate: float
    raw_amount: float
    billed_amount: float
    trust_score: float = 1.0
    invoice_number: str = ""
    is_locked: bool = False
    billable: bool = True
    excluded: bool = False
    conflict: bool = False
    status: str = "Closed"

    def to_standard_csv(self) -> dict[str, object]:
        return {
            "date": self.date,
            "client_name": self.client_name,
            "project_name": self.project_name,
            "project": self.project_code,
            "file": self.file,
            "raw_hours": f"{self.raw_hours:.2f}",
            "billed_hours": f"{self.billed_hours:.2f}",
            "rate": f"{self.rate:.2f}",
            "raw_amount": f"{self.raw_amount:.2f}",
            "billed_amount": f"{self.billed_amount:.2f}",
            "billable": "yes" if self.billable else "no",
        }

    def to_qb_csv(self) -> dict[str, object]:
        description = f"{self.project_label} — {self.file}"
        return {
            "date": self.date,
            "project": self.project_label,
            "description": description,
            "hours": f"{self.billed_hours:.2f}",
            "rate": f"{self.effective_rate:.2f}",
            "amount": f"{self.billed_amount:.2f}",
            "customer": self.client_name,
        }

    def to_accountant_csv(self) -> dict[str, object]:
        memo = f"{self.source} / {self.machine_id}"
        return {
            "date": self.date,
            "client": self.client_name,
            "project": self.project_label,
            "hours": f"{self.billed_hours:.2f}",
            "amount": f"{self.billed_amount:.2f}",
            "taxable": "yes" if self.billable else "no",
            "memo": memo,
        }


@dataclass
class ProjectAggregate:
    project_code: str
    project_name: str
    project_label: str
    client_name: str
    raw_hours: float = 0.0
    billed_hours: float = 0.0
    raw_amount: float = 0.0
    billed_amount: float = 0.0
    trust_score: float = 1.0
    invoice_number: str = ""
    is_locked: bool = False


@dataclass
class ReportDataSet:
    rows: List[ReportRow] = field(default_factory=list)
    filter_summary: str = ""
    from_dt: Optional[datetime] = None
    to_dt: Optional[datetime] = None

    @property
    def active_rows(self) -> List[ReportRow]:
        return [row for row in self.rows if row.billable and not row.excluded]

    def aggregate_by_project(self) -> List[ProjectAggregate]:
        grouped: Dict[str, ProjectAggregate] = {}
        for row in self.active_rows:
            agg = grouped.setdefault(
                row.project_code,
                ProjectAggregate(
                    project_code=row.project_code,
                    project_name=row.project_name,
                    project_label=row.project_label,
                    client_name=row.client_name,
                    trust_score=row.trust_score,
                    invoice_number=row.invoice_number,
                    is_locked=row.is_locked,
                ),
            )
            agg.raw_hours += row.raw_hours
            agg.billed_hours += row.billed_hours
            agg.raw_amount += row.raw_amount
            agg.billed_amount += row.billed_amount
        return sorted(grouped.values(), key=lambda item: item.project_label.lower())


class ReportDataBuilder:
    """Collect merged sessions and apply billing metadata for reports."""

    def __init__(
        self,
        repository: object,
        session_aggregator: SessionAggregator,
        billing_service: BillingService,
        log_service: LogService,
        log_paths: Sequence[str],
        assigned_files: Optional[dict[str, str]] = None,
    ) -> None:
        self.repository = repository
        self.session_aggregator = session_aggregator
        self.billing_service = billing_service
        self.log_service = log_service
        self.log_paths = list(log_paths)
        self.assigned_files = dict(assigned_files or {})
        self._trust_cache: Dict[str, float] = {}

    def build(self, filters: ReportFilter) -> ReportDataSet:
        project_codes = self._project_codes_for_filters(filters)
        rows: List[ReportRow] = []
        for project_code in project_codes:
            sessions = self.session_aggregator.sessions_for_project(
                project_code=project_code,
                log_paths=self.log_paths,
                assigned_files=self.assigned_files,
            )
            project_meta = self._project_meta(project_code)
            trust = self._trust_for_project(project_code)
            from_dt = self._normalize_dt(filters.from_dt)
            to_dt = self._normalize_dt(filters.to_dt)
            for session in sessions:
                session_start = self._normalize_dt(session.start)
                if session_start < from_dt or session_start > to_dt:
                    continue
                rows.append(self._row_from_session(session, project_meta, trust))
        rows.sort(key=lambda item: item.start)
        summary = self._filter_summary(filters)
        return ReportDataSet(
            rows=rows,
            filter_summary=summary,
            from_dt=filters.from_dt,
            to_dt=filters.to_dt,
        )

    def build_for_project(
        self,
        project_code: str,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> ReportDataSet:
        start = from_dt or datetime(1970, 1, 1)
        end = to_dt or datetime(9999, 12, 31, 23, 59, 59)
        return self.build(ReportFilter(from_dt=start, to_dt=end, project_code=project_code))

    def build_for_client(
        self,
        client_id: int,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> ReportDataSet:
        start = from_dt or datetime(1970, 1, 1)
        end = to_dt or datetime(9999, 12, 31, 23, 59, 59)
        return self.build(ReportFilter(from_dt=start, to_dt=end, client_id=client_id))

    def rows_from_unified_sessions(
        self,
        sessions: Sequence[UnifiedSession],
        project_code: str = "",
    ) -> List[ReportRow]:
        code = project_code or (sessions[0].project_id if sessions else "")
        project_meta = self._project_meta(code)
        trust = self._trust_for_project(code) if code else 1.0
        return [self._row_from_session(session, project_meta, trust) for session in sessions]

    def _project_codes_for_filters(self, filters: ReportFilter) -> List[str]:
        if filters.project_code:
            return [filters.project_code]
        codes: set[str] = set()
        for project in self.repository.list_projects(active_only=False):
            if filters.client_id and int(project.client_id) != filters.client_id:
                continue
            codes.add(project.project_code)
        if not filters.client_id:
            for session in self.repository.list_sessions(include_open=True, limit=15000):
                if session.start_time < filters.from_dt or session.start_time > filters.to_dt:
                    continue
                codes.add(session.project_id)
        return sorted(codes)

    def _project_meta(self, project_code: str) -> dict[str, object]:
        project = self.repository.get_project_by_code(project_code)
        client_name = ""
        project_name = project_code
        invoice_number = ""
        is_locked = False
        if project:
            project_name = project.name.strip() or project.project_code.strip()
            client = self.repository.get_client(project.client_id)
            client_name = client.name if client else ""
            invoice_number = project.invoice_number or ""
            is_locked = bool(project.is_locked)
        return {
            "project_name": project_name,
            "project_label": _project_report_label(project_name, project_code),
            "client_name": client_name,
            "invoice_number": invoice_number,
            "is_locked": is_locked,
        }

    def _trust_for_project(self, project_code: str) -> float:
        if project_code in self._trust_cache:
            return self._trust_cache[project_code]
        if not self.log_paths:
            self._trust_cache[project_code] = 1.0
            return 1.0
        summary = self.log_service.get_project_summary(
            project_name=project_code,
            log_paths=self.log_paths,
            aliases=[project_code],
        )
        trust = float(summary.trust_score)
        self._trust_cache[project_code] = trust
        return trust

    def _row_from_session(
        self,
        session: UnifiedSession,
        project_meta: dict[str, object],
        trust_score: float,
    ) -> ReportRow:
        raw_hours = max(0.0, float(session.hours))
        rate = float(session.hourly_rate)
        billable = not session.is_excluded and not session.conflict_ids
        billing = self.billing_service.compute(
            BillingContext(
                rate=rate,
                duration_hours=raw_hours,
                started_at=session.start,
                billable=billable,
            )
        )
        return ReportRow(
            date=session.start.strftime("%Y-%m-%d"),
            start=session.start,
            end=session.end,
            project_code=session.project_id,
            project_name=str(project_meta.get("project_name") or session.project_id),
            project_label=str(
                project_meta.get("project_label")
                or _project_report_label(
                    str(project_meta.get("project_name") or session.project_id),
                    session.project_id,
                )
            ),
            client_name=str(project_meta.get("client_name") or ""),
            file=session.file_alias or session.file_path,
            source=session.source,
            machine_id=session.machine_id,
            raw_hours=raw_hours,
            billed_hours=billing.rounded_hours if billable else 0.0,
            rate=rate,
            effective_rate=billing.effective_rate,
            raw_amount=round(raw_hours * rate, 2),
            billed_amount=billing.total_due,
            trust_score=trust_score,
            invoice_number=str(project_meta.get("invoice_number") or ""),
            is_locked=bool(project_meta.get("is_locked")),
            billable=billable,
            excluded=session.is_excluded,
            conflict=bool(session.conflict_ids),
            status=session.status,
        )

    def _filter_summary(self, filters: ReportFilter) -> str:
        parts = [
            f"{filters.from_dt.strftime('%Y-%m-%d %H:%M')} – {filters.to_dt.strftime('%Y-%m-%d %H:%M')}",
        ]
        if filters.project_code:
            project = self.repository.get_project_by_code(filters.project_code)
            if project:
                label = _project_report_label(project.name, project.project_code)
            else:
                label = filters.project_code
            parts.append(f"Project: {label}")
        if filters.client_id:
            client = self.repository.get_client(filters.client_id)
            if client:
                parts.append(f"Client: {client.name}")
        return " | ".join(parts)

    @staticmethod
    def _normalize_dt(value: datetime) -> datetime:
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value
