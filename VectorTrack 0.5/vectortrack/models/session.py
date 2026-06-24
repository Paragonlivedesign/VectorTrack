"""
Session model for v4 persistence and compatibility with v3 timing logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Optional


@dataclass
class TimeSession:
    project_id: str
    file_path: str
    start_time: datetime
    end_time: Optional[datetime] = None
    hourly_rate: float = 0.0
    rate_overridden: bool = False
    live_duration: timedelta = timedelta()
    log_history_duration: timedelta = timedelta()
    log_current_open_hours: float = 0.0
    balance_delta_hours: float = 0.0
    id: Optional[int] = None
    file_alias: Optional[str] = None
    machine_id: Optional[str] = None
    source: Optional[str] = None

    @property
    def active_duration(self) -> timedelta:
        return self.log_history_duration + self.live_duration

    @property
    def billable_amount(self) -> float:
        hours = self.active_duration.total_seconds() / 3600.0
        return round(hours * self.hourly_rate, 2)

    def sync_active_total(self) -> None:
        """Retained for compatibility with v3 callers that mutate duration fields directly."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "file_path": self.file_path,
            "file_alias": self.file_alias or Path(self.file_path).name,
            "machine_id": self.machine_id,
            "source": self.source,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "hourly_rate": self.hourly_rate,
            "rate_overridden": int(self.rate_overridden),
            "live_duration": self.live_duration.total_seconds(),
            "log_history_duration": self.log_history_duration.total_seconds(),
            "log_current_open_hours": self.log_current_open_hours,
            "balance_delta_hours": self.balance_delta_hours,
            "active_duration": self.active_duration.total_seconds(),
        }

    def to_row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "file_path": self.file_path,
            "file_alias": self.file_alias or Path(self.file_path).name,
            "machine_id": self.machine_id,
            "source": self.source,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "hourly_rate": self.hourly_rate,
            "rate_overridden": int(self.rate_overridden),
            "live_duration": self.live_duration.total_seconds(),
            "log_history_duration": self.log_history_duration.total_seconds(),
            "log_current_open_hours": self.log_current_open_hours,
            "balance_delta_hours": self.balance_delta_hours,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TimeSession":
        working = dict(data)
        start_time = datetime.fromisoformat(str(working["start_time"]))
        end_time = (
            datetime.fromisoformat(str(working["end_time"]))
            if working.get("end_time")
            else None
        )

        if "live_duration" in working:
            live_duration = timedelta(seconds=float(working.get("live_duration", 0) or 0))
        else:
            active = timedelta(seconds=float(working.get("active_duration", 0) or 0))
            log_hist = timedelta(
                seconds=float(working.get("log_history_duration", 0) or 0)
            )
            live_duration = max(timedelta(), active - log_hist)

        return cls(
            id=working.get("id"),
            project_id=str(working["project_id"]),
            file_path=str(working["file_path"]),
            file_alias=working.get("file_alias"),
            machine_id=working.get("machine_id"),
            source=working.get("source"),
            start_time=start_time,
            end_time=end_time,
            hourly_rate=float(working.get("hourly_rate", 0) or 0),
            rate_overridden=bool(int(working.get("rate_overridden", 0) or 0)),
            live_duration=live_duration,
            log_history_duration=timedelta(
                seconds=float(working.get("log_history_duration", 0) or 0)
            ),
            log_current_open_hours=float(working.get("log_current_open_hours", 0) or 0),
            balance_delta_hours=float(working.get("balance_delta_hours", 0) or 0),
        )

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "TimeSession":
        return cls.from_dict(row)
