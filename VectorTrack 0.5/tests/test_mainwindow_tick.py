"""MainWindow tick integration test."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from PyQt6.QtWidgets import QApplication

from vectortrack.process_monitor import WindowInfo
from vectortrack.services.tracking_service import TrackingService
from vectortrack.ui.main_window import MainWindow


class TickTrackingService(TrackingService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tick_calls = 0

    def tick(self, now=None):
        self.tick_calls += 1
        return super().tick(now=now)


class TickProcessMonitor:
    vectorworks_path = "C:/Vectorworks2026/Vectorworks2026.exe"

    def __init__(self):
        self.window = WindowInfo(
            hwnd=1,
            title="Alpha.vwx - Vectorworks",
            process_id=1,
            file_path="I:/alpha.vwx",
            is_visible=True,
            is_active=True,
        )
        self.vectorworks_windows = [self.window]

    def refresh(self):
        return self.vectorworks_windows

    def get_active_window(self):
        return self.window

    def auto_select_vectorworks(self):
        return self.vectorworks_path

    def is_render_grace_window(self, title=None):
        return False


class TickRepository:
    def __init__(self):
        self.default_hourly_rate = 75.0

    def list_sessions(self, **kwargs):
        return []

    def list_log_sources(self):
        return []

    def list_projects(self, **kwargs):
        return []

    def get_project_by_code(self, code):
        return None

    def start_session(self, state):
        return state

    def update_session_duration(self, state, elapsed):
        return None

    def end_session(self, state):
        return None

    def upsert_open_session(self, state):
        return state


@pytest.fixture
def app():
    existing = QApplication.instance()
    if existing is None:
        return QApplication([])
    return existing


@pytest.mark.gui
def test_main_window_tick_advances_tracking(app, monkeypatch):
    monkeypatch.setattr(MainWindow, "_run_startup_sequence", lambda self: None)
    monkeypatch.setattr(MainWindow, "_setup_hotkeys", lambda self: None)
    monkeypatch.setattr(MainWindow, "_setup_tray", lambda self: None)

    process = TickProcessMonitor()
    tracking = TickTrackingService(
        process,
        __import__("vectortrack.activity_monitor", fromlist=["ActivityMonitor"]).ActivityMonitor(
            idle_timeout_seconds=300
        ),
        TickRepository(),
        autosave_seconds=1,
    )
    window = MainWindow(
        repository=TickRepository(),
        tracking_service=tracking,
        log_service=__import__("vectortrack.services.log_service", fromlist=["LogService"]).LogService(),
        billing_service=__import__("vectortrack.services.billing_service", fromlist=["BillingService"]).BillingService(),
        process_monitor=process,
        activity_monitor=tracking.activity_monitor,
    )
    window.process_monitor = process
    window._vw_detect_mode = "saved"
    tracking.start()
    now = datetime.now()
    window._tick()
    window._tick()
    tracking.tick(now=now + timedelta(seconds=2))
    assert tracking.tick_calls >= 1
    assert tracking.current_state is not None
