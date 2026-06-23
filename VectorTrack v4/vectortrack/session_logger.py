"""Compatibility session logger implemented as a thin repository wrapper."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from vectortrack import config
from vectortrack.db.repository import Repository
from vectortrack.models import TimeSession


class SessionLogger:
    """Compatibility API for legacy callers, backed by Repository."""

    def __init__(self, db_path: str | None = None):
        self.db_path = str(Path(db_path) if db_path else config.db_path())
        self.repository = Repository(database_path=Path(self.db_path))

    def start_session(self, project_id: str, file_path: str, hourly_rate: float) -> TimeSession:
        return TimeSession(
            project_id=project_id,
            file_path=file_path,
            start_time=datetime.now(),
            hourly_rate=hourly_rate,
            source="live",
        )

    def end_session(self, session: TimeSession) -> None:
        if not session:
            return
        session.end_time = datetime.now()
        stored = self.repository.upsert_open_session(session)
        if stored.id is not None and session.end_time is not None:
            self.repository.close_session(stored.id, session.end_time.isoformat())

    def update_session_duration(self, session: TimeSession, duration: timedelta) -> None:
        if not session:
            return
        session.live_duration += duration

    def get_project_sessions(
        self,
        project_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[TimeSession]:
        sessions = self.repository.list_sessions(project_id=project_id, include_open=True, limit=5000)
        if start_date is not None:
            sessions = [row for row in sessions if row.start_time >= start_date]
        if end_date is not None:
            sessions = [row for row in sessions if row.start_time <= end_date]
        return sessions

    def generate_report(
        self,
        project_id: str,
        start_date: datetime,
        end_date: datetime,
        output_path: str,
    ) -> None:
        sessions = self.get_project_sessions(project_id, start_date, end_date)
        total_duration = timedelta()
        total_billable = 0.0
        payload = {
            "project_id": project_id,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "sessions": [],
            "summary": {},
        }
        for session in sessions:
            total_duration += session.active_duration
            total_billable += session.billable_amount
            payload["sessions"].append(session.to_dict())
        payload["summary"] = {
            "total_hours": round(total_duration.total_seconds() / 3600.0, 2),
            "total_billable": round(total_billable, 2),
        }
        Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def clear_all_sessions(self) -> None:
        for session in self.repository.list_sessions(include_open=True, limit=100000):
            if session.id is not None:
                self.repository.close_session(session.id, datetime.now().isoformat())