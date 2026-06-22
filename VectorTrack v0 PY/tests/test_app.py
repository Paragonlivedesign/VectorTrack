"""
Tests for the main application module.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QLineEdit
from vectortrack.app import MainWindow
from vectortrack.process_monitor import WindowInfo

@pytest.fixture
def main_window(qtbot):
    """Create the main application window with QtBot."""
    window = MainWindow()
    qtbot.addWidget(window)
    return window

def test_window_initialization(main_window):
    """Test main window initialization."""
    assert main_window.windowTitle() == "VectorTrack"
    assert main_window.current_session is None
    assert main_window.project_id_input.text() == ""
    assert main_window.hourly_rate_input.value() == 75.0
    assert main_window.idle_timeout_input.value() == 5

def test_ui_elements_present(main_window):
    """Test presence of UI elements."""
    assert main_window.project_id_input is not None
    assert main_window.hourly_rate_input is not None
    assert main_window.idle_timeout_input is not None
    assert main_window.status_label is not None
    assert main_window.time_label is not None
    assert main_window.billable_label is not None
    assert main_window.start_button is not None
    assert main_window.report_button is not None
    assert main_window.license_label is not None
    assert main_window.activate_button is not None

@patch('vectortrack.licensing.LicenseManager.check_license_status')
def test_license_check(mock_check_status, main_window, qtbot):
    """Test license status checking."""
    # Test valid license
    mock_check_status.return_value = (True, "Licensed")
    main_window._check_license()
    assert main_window.start_button.isEnabled()
    assert main_window.report_button.isEnabled()
    assert main_window.license_label.text() == "Licensed"
    
    # Test expired license
    mock_check_status.return_value = (False, "Trial period expired")
    main_window._check_license()
    assert not main_window.start_button.isEnabled()
    assert not main_window.report_button.isEnabled()

@patch('PyQt6.QtWidgets.QLineEdit.getText')
@patch('vectortrack.licensing.LicenseManager.activate_license')
def test_license_activation(mock_activate, mock_get_text, main_window, qtbot):
    """Test license activation dialog."""
    mock_get_text.return_value = ("TEST-KEY", True)
    mock_activate.return_value = (True, "License activated successfully")
    
    # Click activate button
    qtbot.mouseClick(main_window.activate_button, Qt.MouseButton.LeftButton)
    
    mock_activate.assert_called_once_with("TEST-KEY")
    assert main_window.start_button.isEnabled()
    assert main_window.report_button.isEnabled()

def test_start_stop_tracking(main_window, qtbot):
    """Test starting and stopping time tracking."""
    # Try starting without project ID
    qtbot.mouseClick(main_window.start_button, Qt.MouseButton.LeftButton)
    assert main_window.current_session is None
    
    # Set project ID and start tracking
    main_window.project_id_input.setText("TEST001")
    qtbot.mouseClick(main_window.start_button, Qt.MouseButton.LeftButton)
    
    assert main_window.current_session is not None
    assert not main_window.project_id_input.isEnabled()
    assert not main_window.hourly_rate_input.isEnabled()
    assert not main_window.idle_timeout_input.isEnabled()
    assert main_window.start_button.text() == "Stop Tracking"
    
    # Stop tracking
    qtbot.mouseClick(main_window.start_button, Qt.MouseButton.LeftButton)
    
    assert main_window.current_session is None
    assert main_window.project_id_input.isEnabled()
    assert main_window.hourly_rate_input.isEnabled()
    assert main_window.idle_timeout_input.isEnabled()
    assert main_window.start_button.text() == "Start Tracking"

@patch('vectortrack.process_monitor.ProcessMonitor.refresh')
def test_status_updates(mock_refresh, main_window, qtbot):
    """Test status display updates."""
    # Start tracking
    main_window.project_id_input.setText("TEST001")
    qtbot.mouseClick(main_window.start_button, Qt.MouseButton.LeftButton)
    
    # Mock Vectorworks window
    mock_refresh.return_value = [
        WindowInfo(123, "test.vwx - Vectorworks", 456, "test.vwx", True, 0)
    ]
    
    # Trigger status update
    main_window._update_status()
    
    assert "test.vwx" in main_window.status_label.text()
    assert main_window.time_label.text() == "00:00:00"
    assert main_window.billable_label.text() == "$0.00"
    
    # Test with no Vectorworks windows
    mock_refresh.return_value = []
    main_window._update_status()
    assert "Waiting for Vectorworks" in main_window.status_label.text()

def test_activity_tracking(main_window, qtbot):
    """Test activity tracking."""
    # Start tracking
    main_window.project_id_input.setText("TEST001")
    qtbot.mouseClick(main_window.start_button, Qt.MouseButton.LeftButton)
    
    # Simulate activity
    main_window._on_activity_change(True)
    assert main_window.current_session is not None
    
    # Simulate inactivity
    main_window._on_activity_change(False)
    
    # Stop tracking
    qtbot.mouseClick(main_window.start_button, Qt.MouseButton.LeftButton)

@patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName')
@patch('vectortrack.session_logger.SessionLogger.generate_report')
def test_report_generation(mock_generate, mock_save_dialog, main_window, qtbot):
    """Test report generation."""
    # Try generating without project ID
    qtbot.mouseClick(main_window.report_button, Qt.MouseButton.LeftButton)
    mock_generate.assert_not_called()
    
    # Set project ID and try again
    main_window.project_id_input.setText("TEST001")
    mock_save_dialog.return_value = ("report.json", "")
    
    qtbot.mouseClick(main_window.report_button, Qt.MouseButton.LeftButton)
    mock_generate.assert_called_once()

def test_window_close(main_window, qtbot):
    """Test window close handling."""
    # Start tracking
    main_window.project_id_input.setText("TEST001")
    qtbot.mouseClick(main_window.start_button, Qt.MouseButton.LeftButton)
    
    # Close window
    main_window.close()
    
    # Session should be ended
    assert main_window.current_session is None 