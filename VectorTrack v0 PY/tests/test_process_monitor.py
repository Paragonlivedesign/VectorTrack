"""
Tests for the process monitor module.
"""

import pytest
from unittest.mock import Mock, patch
from vectortrack.process_monitor import ProcessMonitor, WindowInfo

@pytest.fixture
def process_monitor():
    return ProcessMonitor()

def test_window_info_creation():
    """Test WindowInfo dataclass creation."""
    info = WindowInfo(
        hwnd=123,
        title="Test - Vectorworks",
        process_id=456,
        file_path="Test",
        is_visible=True,
        monitor=0
    )
    assert info.hwnd == 123
    assert info.title == "Test - Vectorworks"
    assert info.process_id == 456
    assert info.file_path == "Test"
    assert info.is_visible is True
    assert info.monitor == 0

@patch('win32gui.IsWindowVisible')
@patch('win32gui.GetWindowText')
@patch('win32process.GetWindowThreadProcessId')
@patch('psutil.Process')
def test_window_enum_callback(mock_process, mock_get_pid, mock_get_text, 
                            mock_is_visible, process_monitor):
    """Test window enumeration callback."""
    # Setup mocks
    mock_is_visible.return_value = True
    mock_get_text.return_value = "Test - Vectorworks"
    mock_get_pid.return_value = (0, 123)
    
    mock_process_obj = Mock()
    mock_process_obj.name.return_value = "Vectorworks.exe"
    mock_process.return_value = mock_process_obj
    
    # Test callback
    windows = []
    process_monitor._window_enum_callback(456, windows)
    
    assert len(windows) == 1
    window = windows[0]
    assert window.hwnd == 456
    assert window.title == "Test - Vectorworks"
    assert window.process_id == 123
    assert window.file_path == "Test"

@patch('win32gui.IsWindowVisible')
@patch('win32gui.GetWindowPlacement')
def test_is_window_visible(mock_placement, mock_is_visible, process_monitor):
    """Test window visibility check."""
    mock_is_visible.return_value = True
    mock_placement.return_value = (0, 1, 0, 0, 0)  # Not minimized
    
    assert process_monitor._is_window_visible(123) is True
    
    # Test minimized window
    mock_placement.return_value = (0, 2, 0, 0, 0)  # SW_SHOWMINIMIZED
    assert process_monitor._is_window_visible(123) is False

def test_get_file_path_from_title(process_monitor):
    """Test file path extraction from window title."""
    title = "MyProject.vwx - Vectorworks"
    assert process_monitor._get_file_path_from_title(title) == "MyProject.vwx"
    
    # Test title without expected format
    title = "Vectorworks"
    assert process_monitor._get_file_path_from_title(title) is None

@patch('win32gui.EnumWindows')
def test_refresh(mock_enum_windows, process_monitor):
    """Test window list refresh."""
    def fake_enum_windows(callback, windows):
        callback(123, windows)
        
    mock_enum_windows.side_effect = fake_enum_windows
    
    with patch.object(process_monitor, '_window_enum_callback') as mock_callback:
        process_monitor.refresh()
        mock_callback.assert_called_once()

@patch('vectortrack.process_monitor.ProcessMonitor.refresh')
def test_is_file_active(mock_refresh, process_monitor):
    """Test file activity check."""
    # Setup test data
    test_file = "test.vwx"
    mock_refresh.return_value = [
        WindowInfo(123, "test.vwx - Vectorworks", 456, test_file, True, 0)
    ]
    
    assert process_monitor.is_file_active(test_file) is True
    
    # Test with inactive window
    mock_refresh.return_value = [
        WindowInfo(123, "test.vwx - Vectorworks", 456, test_file, False, 0)
    ]
    assert process_monitor.is_file_active(test_file) is False
    
    # Test with no windows
    mock_refresh.return_value = []
    assert process_monitor.is_file_active(test_file) is False 