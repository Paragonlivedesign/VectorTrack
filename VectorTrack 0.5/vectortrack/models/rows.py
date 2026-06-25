"""Typed row models for main window tables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class OpenFileRow:
    file_path: str
    project: str
    status: str
    past_hours: float
    live_hours: float
    delta_hours: float
    rate: float
    earned: float
    project_code: str = ""
    file_name: str = ""
    row_kind: str = ""
    is_tracking: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_name": self.file_name or os.path.basename(self.file_path),
            "project": self.project,
            "status": self.status,
            "past_hours": self.past_hours,
            "live_hours": self.live_hours,
            "delta_hours": self.delta_hours,
            "rate": self.rate,
            "earned": self.earned,
            "project_code": self.project_code,
            "row_kind": self.row_kind,
            "is_tracking": self.is_tracking,
        }

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "OpenFileRow":
        return cls(
            file_path=str(row.get("file_path", "")),
            project=str(row.get("project", "")),
            status=str(row.get("status", "")),
            past_hours=float(row.get("past_hours", 0.0)),
            live_hours=float(row.get("live_hours", 0.0)),
            delta_hours=float(row.get("delta_hours", 0.0)),
            rate=float(row.get("rate", 0.0)),
            earned=float(row.get("earned", 0.0)),
            project_code=str(row.get("project_code", "")),
        )


@dataclass
class ProjectSummaryRow:
    project_code: str
    project_name: str
    rate: float
    tracked_hours: float
    billable_hours: float
    billable_amount: float
    budget_hours: float | None = None
    budget_money: float | None = None
    budget_progress: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_code": self.project_code,
            "project_name": self.project_name,
            "rate": self.rate,
            "tracked_hours": self.tracked_hours,
            "billable_hours": self.billable_hours,
            "billable_amount": self.billable_amount,
            "budget_hours": self.budget_hours,
            "budget_money": self.budget_money,
            "budget_progress": self.budget_progress,
        }

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "ProjectSummaryRow":
        return cls(
            project_code=str(row.get("project_code", "")),
            project_name=str(row.get("project_name", "")),
            rate=float(row.get("rate", 0.0)),
            tracked_hours=float(row.get("tracked_hours", 0.0)),
            billable_hours=float(row.get("billable_hours", 0.0)),
            billable_amount=float(row.get("billable_amount", 0.0)),
            budget_hours=row.get("budget_hours"),
            budget_money=row.get("budget_money"),
            budget_progress=float(row.get("budget_progress", 0.0)),
        )
