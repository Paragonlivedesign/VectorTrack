"""Tests for HotkeyService."""

from __future__ import annotations

from pynput import keyboard

from vectortrack.services.hotkey_service import HotkeyService


def test_hotkey_dispatch_invokes_callback() -> None:
    calls: list[str] = []

    def dispatch(callback):
        callback()

    service = HotkeyService(enabled=True, dispatch=dispatch)
    service.register_callback("p", lambda: calls.append("pause"))
    service.set_enabled(True)

    service._pressed = {keyboard.Key.ctrl, keyboard.Key.shift}
    service._on_press(keyboard.KeyCode.from_char("p"))

    assert calls == ["pause"]


def test_hotkey_ignores_when_disabled() -> None:
    calls: list[str] = []
    service = HotkeyService(enabled=False, dispatch=lambda cb: cb())
    service.register_callback("p", lambda: calls.append("pause"))

    service._on_press(keyboard.KeyCode.from_char("p"))
    assert calls == []
