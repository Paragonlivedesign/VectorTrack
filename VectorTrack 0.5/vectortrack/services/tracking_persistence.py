"""Persistence protocol for live tracking sessions."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TrackingPersistence(Protocol):
    def start_session(self, tracking_state: object) -> object: ...

    def update_session_duration(self, tracking_state: object, elapsed_seconds: float) -> None: ...

    def end_session(self, tracking_state: object) -> None: ...

    def upsert_open_session(self, tracking_state: object) -> object: ...
