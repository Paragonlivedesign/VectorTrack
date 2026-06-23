"""
Tests for the activity monitor module.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from vectortrack.activity_monitor import ActivityMonitor


@pytest.fixture
def activity_monitor():
    monitor = ActivityMonitor(idle_timeout_seconds=5)
    yield monitor
    if monitor.is_monitoring:
        monitor.stop()


def test_activity_monitor_initialization():
    monitor = ActivityMonitor(idle_timeout_seconds=10)
    assert monitor.idle_timeout == timedelta(seconds=10)
    assert monitor.is_monitoring is False


def test_start_stop_monitoring(activity_monitor):
    activity_monitor.start()
    assert activity_monitor.is_monitoring is True
    assert activity_monitor._mouse_listener is not None
    assert activity_monitor._keyboard_listener is not None
    assert activity_monitor._check_thread is not None

    activity_monitor.stop()
    assert activity_monitor.is_monitoring is False
    assert activity_monitor._mouse_listener is None
    assert activity_monitor._keyboard_listener is None


def test_activity_callbacks(activity_monitor):
    callback = Mock()
    activity_monitor.add_activity_callback(callback)
    assert callback in activity_monitor._activity_callbacks
    activity_monitor.remove_activity_callback(callback)
    assert callback not in activity_monitor._activity_callbacks


def test_on_activity(activity_monitor):
    callback = Mock()
    activity_monitor.add_activity_callback(callback)
    activity_monitor.last_activity = datetime.now() - timedelta(seconds=10)
    activity_monitor._on_activity()
    callback.assert_called_once_with(True)


def test_is_active(activity_monitor):
    activity_monitor.last_activity = datetime.now()
    assert activity_monitor.is_active() is True

    activity_monitor.last_activity = datetime.now() - timedelta(seconds=10)
    assert activity_monitor.is_active() is False


def test_set_idle_timeout(activity_monitor):
    activity_monitor.set_idle_timeout(30)
    assert activity_monitor.idle_timeout == timedelta(seconds=30)


def test_idle_state_transition(activity_monitor):
    callback = Mock()
    activity_monitor.add_activity_callback(callback)
    activity_monitor._last_state = False  # previously active
    activity_monitor.last_activity = datetime.now() - timedelta(seconds=10)
    activity_monitor.is_monitoring = True

    def stop_after_wait(*_args, **_kwargs):
        activity_monitor.is_monitoring = False

    with patch("threading.Event") as mock_event:
        mock_event.return_value.wait.side_effect = stop_after_wait
        activity_monitor._check_idle_loop()

    assert callback.call_count >= 1


def test_notify_activity_change(activity_monitor):
    callback1 = Mock()
    callback2 = Mock()
    activity_monitor.add_activity_callback(callback1)
    activity_monitor.add_activity_callback(callback2)
    activity_monitor._notify_activity_change(True)
    callback1.assert_called_once_with(True)
    callback2.assert_called_once_with(True)

    error_callback = Mock(side_effect=Exception("Test error"))
    activity_monitor.add_activity_callback(error_callback)
    activity_monitor._notify_activity_change(False)
