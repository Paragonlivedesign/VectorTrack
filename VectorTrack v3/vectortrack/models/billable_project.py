"""
Dataclasses for billable entities persisted in the v4 foundation schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Client:
    name: str
    code: Optional[str] = None
    id: Optional[int] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "is_active": int(self.is_active),
            "created_at": self.created_at or _now_iso(),
            "updated_at": self.updated_at or _now_iso(),
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Client":
        values = dict(row)
        return cls(
            id=values.get("id"),
            name=str(values["name"]),
            code=values.get("code"),
            is_active=bool(values.get("is_active", 1)),
            created_at=values.get("created_at"),
            updated_at=values.get("updated_at"),
        )


@dataclass
class BillableProject:
    client_id: int
    project_code: str
    name: str
    hourly_rate: float
    id: Optional[int] = None
    is_active: bool = True
    is_locked: bool = False
    locked_at: Optional[str] = None
    invoice_number: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "client_id": self.client_id,
            "project_code": self.project_code,
            "name": self.name,
            "hourly_rate": self.hourly_rate,
            "is_active": int(self.is_active),
            "is_locked": int(self.is_locked),
            "locked_at": self.locked_at,
            "invoice_number": self.invoice_number,
            "created_at": self.created_at or _now_iso(),
            "updated_at": self.updated_at or _now_iso(),
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "BillableProject":
        values = dict(row)
        return cls(
            id=values.get("id"),
            client_id=int(values["client_id"]),
            project_code=str(values["project_code"]),
            name=str(values["name"]),
            hourly_rate=float(values.get("hourly_rate", 0.0)),
            is_active=bool(values.get("is_active", 1)),
            is_locked=bool(values.get("is_locked", 0)),
            locked_at=values.get("locked_at"),
            invoice_number=values.get("invoice_number"),
            created_at=values.get("created_at"),
            updated_at=values.get("updated_at"),
        )


@dataclass
class AliasRule:
    project_id: int
    alias_pattern: str
    id: Optional[int] = None
    is_regex: bool = False
    priority: int = 100
    is_active: bool = True
    created_at: Optional[str] = None

    def to_row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "alias_pattern": self.alias_pattern,
            "is_regex": int(self.is_regex),
            "priority": self.priority,
            "is_active": int(self.is_active),
            "created_at": self.created_at or _now_iso(),
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "AliasRule":
        values = dict(row)
        return cls(
            id=values.get("id"),
            project_id=int(values["project_id"]),
            alias_pattern=str(values["alias_pattern"]),
            is_regex=bool(values.get("is_regex", 0)),
            priority=int(values.get("priority", 100)),
            is_active=bool(values.get("is_active", 1)),
            created_at=values.get("created_at"),
        )
