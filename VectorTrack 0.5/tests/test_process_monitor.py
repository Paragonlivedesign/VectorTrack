"""
Tests for the process monitor module.
"""

from pathlib import Path
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


@patch("win32gui.IsWindow")
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
    mock_is_window,
    process_monitor,
):
    mock_is_window.return_value = True
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


@patch("win32gui.IsWindow")
@patch("win32gui.IsWindowVisible")
@patch("win32gui.GetWindowPlacement")
def test_is_window_visible(mock_placement, mock_is_visible, mock_is_window, process_monitor):
    mock_is_window.return_value = True
    mock_is_visible.return_value = True
    mock_placement.return_value = (0, 1, 0, 0, 0)
    assert process_monitor._is_window_visible(123) is True

    mock_placement.return_value = (0, 2, 0, 0, 0)
    assert process_monitor._is_window_visible(123) is False


def test_get_file_path_from_title(process_monitor):
    assert process_monitor._get_file_path_from_title("MyProject.vwx - Vectorworks") == "MyProject.vwx"
    assert process_monitor._get_file_path_from_title("Vectorworks") is None
    assert (
        process_monitor._get_file_path_from_title("Vectorworks Spotlight 2026 - [CCC Exhibit Hall v2026.vwx]")
        == "CCC Exhibit Hall v2026.vwx"
    )
    assert (
        process_monitor._get_file_path_from_title(
            r"Vectorworks Spotlight 2026 - [*C:\Projects\Draft.vwx]"
        )
        == r"C:\Projects\Draft.vwx"
    )
    assert (
        process_monitor._get_file_path_from_title("*MyProject.vwx - Vectorworks")
        == "MyProject.vwx"
    )


@patch("win32gui.IsWindow")
@patch("win32gui.EnumChildWindows")
@patch("win32gui.IsWindowVisible")
@patch("win32gui.GetWindowText")
@patch("win32process.GetWindowThreadProcessId")
@patch("psutil.Process")
def test_window_enum_uses_title_only(
    mock_process,
    mock_get_pid,
    mock_get_text,
    mock_is_visible,
    mock_enum_child_windows,
    mock_is_window,
    process_monitor,
):
    mock_is_window.return_value = True
    mock_is_visible.return_value = True
    mock_get_text.return_value = "Vectorworks Spotlight 2026 - [Project.vwx]"
    mock_get_pid.return_value = (0, 123)
    mock_process_obj = Mock()
    mock_process_obj.name.return_value = "Vectorworks.exe"
    mock_process.return_value = mock_process_obj

    windows = []
    process_monitor._window_enum_callback(456, windows)

    mock_enum_child_windows.assert_not_called()
    assert len(windows) == 1
    assert windows[0].file_path == "Project.vwx"


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


def test_suggested_exe_browse_directory_uses_latest_install(tmp_path):
    monitor = ProcessMonitor()
    installs = {
        "Vectorworks 2025": str(tmp_path / "vw" / "2025" / "Vectorworks.exe"),
    }
    for exe in installs.values():
        Path(exe).parent.mkdir(parents=True, exist_ok=True)
        Path(exe).write_text("", encoding="utf-8")
    monitor._known_paths = installs
    assert monitor.suggested_exe_browse_directory() == str(tmp_path / "vw" / "2025")


def test_suggested_exe_browse_directory_falls_back_to_program_files(monkeypatch):
    monitor = ProcessMonitor()
    monitor._known_paths = {}
    monkeypatch.setattr(monitor, "find_vectorworks_installations", lambda: {})
    monkeypatch.setenv("ProgramFiles", r"C:\Program Files")
    suggested = monitor.suggested_exe_browse_directory()
    assert "Program Files" in suggested


def test_find_vectorworks_installations_finds_year_named_folder(tmp_path, monkeypatch):
    exe_path = tmp_path / "Vectorworks 2026" / "Vectorworks 2026.exe"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.delenv("ProgramFiles(x86)", raising=False)

    monitor = ProcessMonitor()
    installs = monitor.find_vectorworks_installations()

    assert installs["Vectorworks 2026"] == str(exe_path)


def test_auto_select_vectorworks_uses_running_process(tmp_path, monkeypatch):
    exe_path = tmp_path / "Vectorworks2026.exe"
    exe_path.write_text("", encoding="utf-8")
    monitor = ProcessMonitor()
    monkeypatch.setattr(monitor, "find_vectorworks_installations", lambda: {})
    monkeypatch.setattr(
        monitor,
        "detect_running_vectorworks_exe",
        lambda: str(exe_path),
    )

    selected = monitor.auto_select_vectorworks()

    assert selected == str(exe_path)
    assert monitor.vectorworks_path == str(exe_path)


def test_latest_known_exe_returns_newest_install(tmp_path):
    monitor = ProcessMonitor()
    monitor._known_paths = {
        "Vectorworks 2024": str(tmp_path / "2024" / "Vectorworks.exe"),
        "Vectorworks 2026": str(tmp_path / "2026" / "Vectorworks.exe"),
    }
    assert monitor.latest_known_exe() == str(tmp_path / "2026" / "Vectorworks.exe")
