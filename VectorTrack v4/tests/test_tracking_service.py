from __future__ import annotations

from datetime import datetime, timedelta

from vectortrack.process_monitor import WindowInfo
from vectortrack.services.tracking_service import TrackingService


class FakeActivityMonitor:
    def __init__(self, active: bool = True):
        self._active = active
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def is_active(self) -> bool:
        return self._active


class FakeProcessMonitor:
    def __init__(self, file_path: str = "I:/jobs/alpha.vwx"):
        self.window = WindowInfo(
            hwnd=1,
            title="Alpha.vwx - Vectorworks",
            process_id=101,
            file_path=file_path,
            is_visible=True,
            is_active=True,
        )

    def refresh(self):
        return [self.window]

    def get_active_window(self):
        return self.window


class FakeRepository:
    def __init__(self):
        self.started = []
        self.updated = []
        self.ended = []
        self.saved = []

    def start_session(self, state):
        self.started.append((state.project_id, state.file_path))

    def update_session_duration(self, state, elapsed):
        self.updated.append((state.file_path, elapsed, state.tracked_seconds))

    def end_session(self, state):
        self.ended.append(state.file_path)

    def save_session(self, state):
        self.saved.append(state.file_path)


def test_tick_tracks_active_foreground_file():
    process = FakeProcessMonitor()
    activity = FakeActivityMonitor(active=True)
    repo = FakeRepository()
    svc = TrackingService(process, activity, repo, autosave_seconds=1)

    svc.start()
    now = datetime.now()
    svc.tick(now=now)
    svc.tick(now=now + timedelta(seconds=12))

    assert svc.current_state is not None
    assert svc.current_state.file_path == "I:/jobs/alpha.vwx"
    assert svc.current_state.tracked_seconds >= 12
    assert repo.started
    assert repo.updated


def test_meeting_mode_auto_expires_after_30_minutes():
    process = FakeProcessMonitor()
    activity = FakeActivityMonitor(active=True)
    repo = FakeRepository()
    svc = TrackingService(process, activity, repo, meeting_duration_minutes=30)

    svc.start()
    state = svc.enable_meeting_mode("Client Sync")
    start = state.last_tick_at

    still_active = svc.tick(now=start + timedelta(minutes=29, seconds=30))
    assert still_active is not None

    expired = svc.tick(now=start + timedelta(minutes=31))
    assert expired is None
    assert svc.meeting_topic is None
    assert svc.current_state is None
    assert repo.ended
