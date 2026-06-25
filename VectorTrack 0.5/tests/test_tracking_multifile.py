"""Additional TrackingService lifecycle tests."""

from __future__ import annotations

from datetime import datetime, timedelta

from vectortrack.process_monitor import WindowInfo
from vectortrack.services.tracking_service import TrackingService


class FakeActivityMonitor:
    def __init__(self, active: bool = True):
        self._active = active

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def is_active(self) -> bool:
        return self._active


class FakeProcessMonitor:
    def __init__(self, files: list[str], foreground_index: int = 0):
        self.files = files
        self.foreground_index = foreground_index
        self.vectorworks_windows = []

    def refresh(self):
        self.vectorworks_windows = [
            WindowInfo(
                hwnd=i + 1,
                title=f"{path} - Vectorworks",
                process_id=100 + i,
                file_path=path,
                is_visible=True,
                is_active=i == self.foreground_index,
            )
            for i, path in enumerate(self.files)
        ]
        return self.vectorworks_windows

    def get_active_window(self):
        if not self.files:
            return None
        return self.vectorworks_windows[self.foreground_index]

    def is_render_grace_window(self, title=None) -> bool:
        return False


class FakeRepository:
    def __init__(self):
        self.started: list[str] = []
        self.updated: list[str] = []
        self.ended: list[str] = []
        self.upserted: list[str] = []

    def start_session(self, state):
        self.started.append(state.file_path)

    def update_session_duration(self, state, elapsed):
        self.updated.append(state.file_path)

    def end_session(self, state):
        self.ended.append(state.file_path)

    def upsert_open_session(self, state):
        self.upserted.append(state.file_path)
        return state


def test_switch_between_open_files():
    process = FakeProcessMonitor(["I:/a.vwx", "I:/b.vwx"], foreground_index=0)
    repo = FakeRepository()
    svc = TrackingService(process, FakeActivityMonitor(), repo, autosave_seconds=1)
    svc.start()
    now = datetime.now()
    svc.tick(now=now)
    process.foreground_index = 1
    svc.tick(now=now + timedelta(seconds=5))
    assert "I:/a.vwx" in repo.ended
    assert "I:/b.vwx" in repo.started


def test_stop_ends_open_session():
    process = FakeProcessMonitor(["I:/a.vwx"])
    repo = FakeRepository()
    svc = TrackingService(process, FakeActivityMonitor(), repo)
    svc.start()
    svc.tick()
    svc.stop()
    assert repo.ended == ["I:/a.vwx"]


def test_render_grace_keeps_current_file():
    process = FakeProcessMonitor(["I:/a.vwx"], foreground_index=0)
    repo = FakeRepository()
    svc = TrackingService(process, FakeActivityMonitor(), repo, autosave_seconds=1)
    svc.start()
    now = datetime.now()
    svc.tick(now=now)
    process.get_active_window = lambda: None  # type: ignore[method-assign]
    process.is_render_grace_window = lambda title=None: True  # type: ignore[method-assign]
    svc.tick(now=now + timedelta(seconds=3))
    assert svc.current_state is not None
    assert svc.current_state.file_path == "I:/a.vwx"
