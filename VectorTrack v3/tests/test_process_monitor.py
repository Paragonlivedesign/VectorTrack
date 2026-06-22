"""
Tests for the process monitor module.
"""

from unittest.mock import Mock, patch

import pytest

from vectortrack.process_monitor import ProcessMonitor, WindowInfo


@pytest.fixture
def process_monitor(tmp_path):
    exe_path = tmp_path / "Vectorworks.exe"
    exe_path.write_text("", encoding="utf-8")
    monitor = ProcessMonitor()
    monitor.set_vectorworks_path(str(exe_path))
    return monitor


def test_window_info_creation():
    info = WindowInfo(
        hwnd=123,
        title="Test.vwx - Vectorworks",
        process_id=456,
        file_path="Test.vwx",
        is_visible=True,
        monitor=0,
    )
    assert info.hwnd == 123
    assert info.file_path == "Test.vwx"


@patch("win32gui.IsWindowVisible")
@patch("win32gui.GetWindowText")
@patch("win32gui.GetClassName")
@patch("win32process.GetWindowThreadProcessId")
@patch("psutil.Process")
def test_window_enum_callback(
    mock_process,
    mock_get_pid,
    mock_get_class,
    mock_get_text,
    mock_is_visible,
    process_monitor,
):
    mock_is_visible.return_value = True
    mock_get_text.return_value = "Test.vwx - Vectorworks"
    mock_get_class.return_value = "VectorworksFrame"
    mock_get_pid.return_value = (0, 123)

    mock_process_obj = Mock()
    mock_process_obj.name.return_value = "Vectorworks.exe"
    mock_process.return_value = mock_process_obj

    windows = []
    process_monitor._window_enum_callback(456, windows)

    assert len(windows) == 1
    window = windows[0]
    assert window.hwnd == 456
    assert window.file_path == "Test.vwx"


@patch("win32gui.IsWindowVisible")
@patch("win32gui.GetWindowPlacement")
def test_is_window_visible(mock_placement, mock_is_visible, process_monitor):
    mock_is_visible.return_value = True
    mock_placement.return_value = (0, 1, 0, 0, 0)
    assert process_monitor._is_window_visible(123) is True

    mock_placement.return_value = (0, 2, 0, 0, 0)
    assert process_monitor._is_window_visible(123) is False


def test_get_file_path_from_title(process_monitor):
    assert process_monitor._get_file_path_from_title("MyProject.vwx - Vectorworks") == "MyProject.vwx"
    assert process_monitor._get_file_path_from_title("Vectorworks") is None


@patch("win32gui.EnumWindows")
def test_refresh(mock_enum_windows, process_monitor):
    def fake_enum_windows(callback, windows):
        callback(123, windows)

    mock_enum_windows.side_effect = fake_enum_windows

    with patch.object(process_monitor, "_window_enum_callback") as mock_callback:
        process_monitor.refresh()
        mock_callback.assert_called_once_with(123, process_monitor.vectorworks_windows)


def test_is_file_active(process_monitor):
    process_monitor.vectorworks_windows = [
        WindowInfo(123, "test.vwx - Vectorworks", 456, "test.vwx", True, 0)
    ]

    with patch.object(process_monitor, "refresh", return_value=process_monitor.vectorworks_windows):
        assert process_monitor.is_file_active("test.vwx") is True

    process_monitor.vectorworks_windows = [
        WindowInfo(123, "test.vwx - Vectorworks", 456, "test.vwx", False, 0)
    ]
    with patch.object(process_monitor, "refresh", return_value=process_monitor.vectorworks_windows):
        assert process_monitor.is_file_active("test.vwx") is False

    process_monitor.vectorworks_windows = []
    with patch.object(process_monitor, "refresh", return_value=process_monitor.vectorworks_windows):
        assert process_monitor.is_file_active("test.vwx") is False


def test_get_foreground_file(process_monitor):
    process_monitor.vectorworks_windows = [
        WindowInfo(100, "A.vwx", 1000, "A.vwx", True, True, 0),
        WindowInfo(200, "B.vwx", 2000, "B.vwx", True, False, 0),
    ]
    with patch("win32gui.GetForegroundWindow", return_value=100):
        assert process_monitor.get_foreground_file() == "A.vwx"


def test_is_render_grace_window(process_monitor):
    assert process_monitor.is_render_grace_window("Rendering viewport") is True
    assert process_monitor.is_render_grace_window("Project.vwx - Vectorworks") is False


@patch("win32gui.GetForegroundWindow")
@patch("win32gui.EnumWindows")
def test_refresh_detects_closed_files(mock_enum_windows, mock_foreground, process_monitor):
    process_monitor.vectorworks_windows = [
        WindowInfo(10, "Old.vwx", 10, "Old.vwx", True, False, 0)
    ]
    mock_foreground.return_value = 20

    def fake_enum(callback, windows):
        windows.append(WindowInfo(20, "New.vwx", 20, "New.vwx", True, False, 0))

    mock_enum_windows.side_effect = fake_enum
    process_monitor.refresh()

    closed = process_monitor.get_closed_files()
    assert "Old.vwx" in closed
    assert process_monitor.vectorworks_windows[0].is_active is True
