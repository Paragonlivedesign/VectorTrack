"""Tests for notification delivery helpers."""

from __future__ import annotations

import subprocess
import sys

import pytest

from vectortrack.services.notification_service import NotificationService, hidden_subprocess_kwargs


class _FakeTray:
    def __init__(self, visible: bool = True) -> None:
        self.visible = visible
        self.messages: list[tuple[str, str]] = []

    def isVisible(self) -> bool:
        return self.visible

    def showMessage(self, title: str, message: str, *_args, **_kwargs) -> None:
        self.messages.append((title, message))


def test_notify_uses_tray_without_subprocess(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(args, **_kwargs):
        calls.append(list(args))

    monkeypatch.setattr(subprocess, "run", fake_run)
    service = NotificationService(enabled=True)
    tray = _FakeTray()
    service.set_tray(tray)

    service.notify("Save test", "hello")

    assert tray.messages == [("VectorTrack - Save test", "hello")]
    assert calls == []


def test_powershell_fallback_hides_console_window(monkeypatch):
    captured: dict = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(subprocess, "run", fake_run)
    service = NotificationService(enabled=True)
    service.set_tray(_FakeTray(visible=False))

    service.notify("Fallback", "message")

    assert captured["args"][:4] == ["powershell", "-NoProfile", "-WindowStyle", "Hidden"]
    if sys.platform == "win32":
        assert captured["kwargs"].get("creationflags") == subprocess.CREATE_NO_WINDOW


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only helper")
def test_hidden_subprocess_kwargs_sets_create_no_window():
    kwargs = hidden_subprocess_kwargs()
    assert kwargs.get("creationflags") == subprocess.CREATE_NO_WINDOW
