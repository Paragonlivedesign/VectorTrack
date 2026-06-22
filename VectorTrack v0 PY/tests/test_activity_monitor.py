"""
Tests for the activity monitor module.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import threading
from vectortrack.activity_monitor import ActivityMonitor

@pytest.fixture
def activity_monitor():
    monitor = ActivityMonitor(idle_timeout_seconds=5)
    yield monitor
    # Cleanup
    if monitor.is_monitoring:
        monitor.stop()

def test_activity_monitor_initialization():
    """Test ActivityMonitor initialization."""
    monitor = ActivityMonitor(idle_timeout_seconds=10)
    assert monitor.idle_timeout == timedelta(seconds=10)
    assert monitor.is_monitoring is False
    assert monitor._mouse_listener is None
    assert monitor._keyboard_listener is None
    assert monitor._activity_callbacks == []

def test_start_stop_monitoring(activity_monitor):
    """Test starting and stopping activity monitoring."""
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
    """Test activity callback registration."""
    callback = Mock()
    
    activity_monitor.add_activity_callback(callback)
    assert callback in activity_monitor._activity_callbacks
    
    activity_monitor.remove_activity_callback(callback)
    assert callback not in activity_monitor._activity_callbacks

@patch('threading.Event')
def test_on_activity(mock_event, activity_monitor):
    """Test activity detection."""
    callback = Mock()
    activity_monitor.add_activity_callback(callback)
    
    # Simulate idle timeout
    activity_monitor.last_activity = datetime.now() - timedelta(seconds=10)
    activity_monitor._on_activity()
    
    # Callback should be called with True (active)
    callback.assert_called_once_with(True)

def test_is_active(activity_monitor):
    """Test activity status check."""
    # Set recent activity
    activity_monitor.last_activity = datetime.now()
    assert activity_monitor.is_active() is True
    
    # Set old activity
    activity_monitor.last_activity = datetime.now() - timedelta(seconds=10)
    assert activity_monitor.is_active() is False

def test_set_idle_timeout(activity_monitor):
    """Test idle timeout configuration."""
    activity_monitor.set_idle_timeout(30)
    assert activity_monitor.idle_timeout == timedelta(seconds=30)

@patch('threading.Event')
def test_check_idle_loop(mock_event, activity_monitor):
    """Test idle state checking loop."""
    callback = Mock()
    activity_monitor.add_activity_callback(callback)
    
    # Start monitoring
    activity_monitor.start()
    
    # Simulate activity
    activity_monitor.last_activity = datetime.now()
    activity_monitor._check_idle_loop()
    
    # Simulate idle
    activity_monitor.last_activity = datetime.now() - timedelta(seconds=10)
    activity_monitor._check_idle_loop()
    
    # Stop monitoring
    activity_monitor.stop()
    
    # Callback should be called at least once
    assert callback.call_count > 0

def test_notify_activity_change(activity_monitor):
    """Test activity change notification."""
    callback1 = Mock()
    callback2 = Mock()
    
    activity_monitor.add_activity_callback(callback1)
    activity_monitor.add_activity_callback(callback2)
    
    activity_monitor._notify_activity_change(True)
    
    callback1.assert_called_once_with(True)
    callback2.assert_called_once_with(True)
    
    # Test error handling
    error_callback = Mock(side_effect=Exception("Test error"))
    activity_monitor.add_activity_callback(error_callback)
    
    # Should not raise exception
    activity_monitor._notify_activity_change(False) 