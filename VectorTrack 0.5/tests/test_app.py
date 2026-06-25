"""MainWindow smoke tests for VectorTrack 0.5."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest
from PyQt6.QtWidgets import QApplication, QWidget

from vectortrack.ui.main_window import MainWindow


class _FakeRepository:
    def list_sessions(self, *args, **kwargs):
        return []

    def list_projects(self, *args, **kwargs):
        return []

    def get_project_by_code(self, _code: str):
        return None


@dataclass
class _FakeWindowInfo:
    file_path: Optional[str] = None


class _FakeProcessMonitor:
    def __init__(self) -> None:
        self.vectorworks_path = ""

    def auto_select_vectorworks(self):
        return None

    def set_vectorworks_path(self, path: str) -> None:
        self.vectorworks_path = path

    def refresh(self):
        return []

    def get_active_window(self):
        return _FakeWindowInfo()


class _FakeActivityMonitor:
    def set_idle_timeout(self, _seconds: int) -> None:
        return None


class _FakeTrackingService:
    def __init__(self) -> None:
        self.states_by_file = {}
        self.is_paused = False
        self.current_state = None

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def tick(self) -> None:
        return None

    def set_paused(self, _paused: bool) -> None:
        return None


class _FakeTray:
    def __init__(self, _parent) -> None:
        self.visible = False
        self.status = "inactive"
        self.paused = False

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def set_tracking_status(self, status: str) -> None:
        self.status = status

    def set_paused(self, paused: bool) -> None:
        self.paused = paused


class _FakeHud(QWidget):
    def set_stats(self, *_args, **_kwargs) -> None:
        return None


def _create_window(monkeypatch) -> MainWindow:
    monkeypatch.setattr("vectortrack.ui.main_window.VectorTrackTray", _FakeTray)
    monkeypatch.setattr("vectortrack.ui.main_window.HUDWindow", _FakeHud)
    return MainWindow(
        repository=_FakeRepository(),
        tracking_service=_FakeTrackingService(),
        log_service=object(),
        billing_service=object(),
        process_monitor=_FakeProcessMonitor(),
        activity_monitor=_FakeActivityMonitor(),
    )


@pytest.fixture
def app():
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    yield instance
    instance.processEvents()


@pytest.mark.gui
def test_main_window_smoke_constructs_and_titles(app, monkeypatch):
    window = _create_window(monkeypatch)

    assert window.windowTitle() == "VectorTrack"
    assert window.bottom_tabs.count() >= 2
    window.close()
    app.processEvents()


@pytest.mark.gui
def test_main_window_show_and_close_smoke(app, monkeypatch):
    window = _create_window(monkeypatch)

    window.show()
    app.processEvents()
    assert window.isVisible()

    window.close()
    app.processEvents()
    assert not window.isVisible()
