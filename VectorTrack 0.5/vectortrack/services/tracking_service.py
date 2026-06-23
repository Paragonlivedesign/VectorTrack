"""Tracking orchestration service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

from ..activity_monitor import ActivityMonitor
from ..config import DEFAULT_IDLE_BYPASS_MODE, DEFAULT_IDLE_PAUSE_ENABLED, IDLE_BYPASS_MODES
from ..process_monitor import ProcessMonitor, WindowInfo


UNTITLED_TOKENS = ("untitled", "opening file:")


@dataclass
class TrackingState:
    file_path: str
    project_id: str
    started_at: datetime
    last_tick_at: datetime
    tracked_seconds: float = 0.0
    meeting_mode: bool = False

    @property
    def tracked_hours(self) -> float:
        return self.tracked_seconds / 3600


class TrackingService:
    """
    v4 tracking coordinator.

    Integrates ProcessMonitor + ActivityMonitor + repository persistence while
    enforcing frontmost-only tracking.
    """

    def __init__(
        self,
        process_monitor: ProcessMonitor,
        activity_monitor: ActivityMonitor,
        repository: object,
        autosave_seconds: int = 30,
        meeting_duration_minutes: int = 30,
        untitled_hook: Optional[Callable[[str], None]] = None,
    ):
        self.process_monitor = process_monitor
        self.activity_monitor = activity_monitor
        self.repository = repository
        self.autosave_interval = timedelta(seconds=autosave_seconds)
        self.meeting_duration = timedelta(minutes=meeting_duration_minutes)
        self.untitled_hook = untitled_hook

        self.current_state: Optional[TrackingState] = None
        self.states_by_file: Dict[str, TrackingState] = {}
        self.is_running = False
        self.is_paused = False
        self.last_autosave_at: Optional[datetime] = None
        self.meeting_topic: Optional[str] = None
        self.meeting_expires_at: Optional[datetime] = None
        self.idle_pause_enabled = DEFAULT_IDLE_PAUSE_ENABLED
        self.idle_bypass_mode = DEFAULT_IDLE_BYPASS_MODE
        self.log_open_checker: Optional[Callable[[str], bool]] = None

    def set_idle_pause_enabled(self, enabled: bool) -> None:
        self.idle_pause_enabled = bool(enabled)

    def set_idle_bypass_mode(self, mode: str) -> None:
        if mode in IDLE_BYPASS_MODES:
            self.idle_bypass_mode = mode

    def should_count_time(self, file_path: str) -> bool:
        if self.is_paused:
            return False
        return self._should_advance_time(file_path)

    def is_idle_blocked(self, file_path: str) -> bool:
        if self.is_paused or not self.idle_pause_enabled:
            return False
        if self.activity_monitor.is_active():
            return False
        return not self._idle_bypass_active(file_path)

    def start(self) -> None:
        self.is_running = True
        self.activity_monitor.start()
        self.last_autosave_at = datetime.now()

    def stop(self) -> None:
        self.is_running = False
        self._end_current_session()
        self.activity_monitor.stop()

    def set_paused(self, paused: bool) -> None:
        self.is_paused = paused

    def enable_meeting_mode(self, topic: str = "Meeting") -> TrackingState:
        synthetic_path = f"__meeting__/{topic.strip() or 'Meeting'}"
        self.meeting_topic = topic.strip() or "Meeting"
        self.meeting_expires_at = datetime.now() + self.meeting_duration
        state = self._switch_to_file(synthetic_path, is_meeting=True)
        return state

    def disable_meeting_mode(self) -> None:
        self.meeting_topic = None
        self.meeting_expires_at = None
        if self.current_state and self.current_state.meeting_mode:
            self._end_current_session()

    def tick(self, now: Optional[datetime] = None) -> Optional[TrackingState]:
        if not self.is_running:
            return None
        if now is None:
            now = datetime.now()

        if self.meeting_topic:
            state = self.current_state or self.enable_meeting_mode(self.meeting_topic)
            if self.meeting_expires_at and now >= self.meeting_expires_at:
                self._advance_state(state, self.meeting_expires_at)
                self._autosave_if_needed(self.meeting_expires_at)
                self.disable_meeting_mode()
                return None
            self._advance_state(state, now)
            self._autosave_if_needed(now)
            return state

        windows = self.process_monitor.refresh()
        active_window = self.process_monitor.get_active_window()
        open_paths = {window.file_path for window in windows if window.file_path}

        file_path: Optional[str] = None
        if active_window and active_window.file_path and not self._is_untitled(active_window.file_path):
            file_path = active_window.file_path
        elif (
            self.idle_bypass_mode == "vw_file_open"
            and self.current_state
            and self.current_state.file_path in open_paths
            and self.idle_pause_enabled
            and not self.activity_monitor.is_active()
            and not self.is_paused
        ):
            file_path = self.current_state.file_path

        if not file_path:
            return self.current_state

        if self._is_untitled(file_path):
            if self.untitled_hook:
                self.untitled_hook(file_path)
            return self.current_state

        if self.current_state is None or self.current_state.file_path != file_path:
            self._switch_to_file(file_path)

        if self.current_state and self._should_advance_time(file_path) and not self.is_paused:
            self._advance_state(self.current_state, now)
        self._autosave_if_needed(now)
        return self.current_state

    def _should_advance_time(self, file_path: str) -> bool:
        if not self.idle_pause_enabled:
            return True
        if self.activity_monitor.is_active():
            return True
        return self._idle_bypass_active(file_path)

    def _idle_bypass_active(self, file_path: str) -> bool:
        mode = self.idle_bypass_mode
        if mode == "none":
            return False
        if mode == "vw_foreground":
            active_window = self.process_monitor.get_active_window()
            return bool(active_window and active_window.file_path == file_path)
        if mode == "vw_file_open":
            windows = self.process_monitor.refresh()
            open_paths = {window.file_path for window in windows if window.file_path}
            return file_path in open_paths
        if mode == "log_open":
            if self.log_open_checker is None:
                return False
            return bool(self.log_open_checker(file_path))
        return False

    def _switch_to_file(self, file_path: str, is_meeting: bool = False) -> TrackingState:
        self._end_current_session()
        now = datetime.now()
        if file_path in self.states_by_file:
            state = self.states_by_file[file_path]
            state.last_tick_at = now
        else:
            state = TrackingState(
                file_path=file_path,
                project_id=self._project_id_for(file_path),
                started_at=now,
                last_tick_at=now,
                meeting_mode=is_meeting,
            )
            self.states_by_file[file_path] = state
            self._repository_call("start_session", state)
        state.meeting_mode = is_meeting
        self.current_state = state
        return state

    def _advance_state(self, state: TrackingState, now: datetime) -> None:
        elapsed = max(0.0, (now - state.last_tick_at).total_seconds())
        state.last_tick_at = now
        if elapsed <= 0:
            return
        state.tracked_seconds += elapsed
        self._repository_call("update_session_duration", state, elapsed)

    def _autosave_if_needed(self, now: datetime) -> None:
        if not self.current_state:
            return
        if self.last_autosave_at and (now - self.last_autosave_at) < self.autosave_interval:
            return
        self.last_autosave_at = now
        for method in ("save_session", "upsert_session", "save_tracking_state", "autosave"):
            if self._repository_call(method, self.current_state):
                break

    def _end_current_session(self) -> None:
        if not self.current_state:
            return
        self._repository_call("end_session", self.current_state)
        self.current_state = None

    def _repository_call(self, method_name: str, *args) -> bool:
        method = getattr(self.repository, method_name, None)
        if not callable(method):
            return False
        method(*args)
        return True

    @staticmethod
    def _project_id_for(file_path: str) -> str:
        if file_path.startswith("__meeting__/"):
            return os.path.basename(file_path) or "Meeting"
        return ""

    @staticmethod
    def _is_untitled(file_path: str) -> bool:
        lowered = file_path.lower().strip()
        return any(token in lowered for token in UNTITLED_TOKENS)
