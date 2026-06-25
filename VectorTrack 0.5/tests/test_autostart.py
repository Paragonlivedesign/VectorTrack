"""Tests for Windows autostart registration helpers."""

from __future__ import annotations

from vectortrack.services.autostart import START_IN_TRAY_FLAG, startup_command


def test_startup_command_includes_start_in_tray_flag():
    command = startup_command(r"C:\Apps\VectorTrack.exe")
    assert command == f'"C:\\Apps\\VectorTrack.exe" {START_IN_TRAY_FLAG}'


def test_startup_command_for_python_entrypoint(monkeypatch):
    monkeypatch.setattr("vectortrack.services.autostart.sys.executable", r"C:\Python\python.exe")
    command = startup_command(r"C:\Dev\VectorTrack 0.5\run.py")
    assert command == (
        f'"C:\\Python\\python.exe" "C:\\Dev\\VectorTrack 0.5\\run.py" {START_IN_TRAY_FLAG}'
    )
