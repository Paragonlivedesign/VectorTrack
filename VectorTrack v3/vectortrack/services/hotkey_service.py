"""Global hotkey handling for VectorTrack."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loguru import logger
from pynput import keyboard


HotkeyCallback = Callable[[], None]


class HotkeyService:
    """
    Listen for global Ctrl+Shift hotkeys.

    Default bindings:
    - Ctrl+Shift+P: pause toggle
    - Ctrl+Shift+M: meeting mode
    - Ctrl+Shift+R: refresh
    - Ctrl+Shift+H: HUD toggle
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._pressed: set[Any] = set()
        self._listener: keyboard.Listener | None = None
        self._callbacks: dict[str, HotkeyCallback] = {}

    def register_callback(self, key: str, callback: HotkeyCallback) -> None:
        self._callbacks[key.lower()] = callback

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def start(self) -> None:
        if self._listener is not None:
            return
        if not self.enabled:
            logger.info("Hotkey service disabled; listener not started")
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        logger.info("Hotkey service started")

    def stop(self) -> None:
        if self._listener is None:
            return
        try:
            self._listener.stop()
        except Exception as exc:  # pragma: no cover - defensive cleanup
            logger.debug(f"Hotkey listener stop error: {exc}")
        self._listener = None
        self._pressed.clear()
        logger.info("Hotkey service stopped")

    def _on_press(self, key: Any) -> None:
        if not self.enabled:
            return
        self._pressed.add(key)
        if not self._ctrl_shift_down():
            return

        letter = self._key_letter(key)
        if not letter:
            return
        callback = self._callbacks.get(letter)
        if not callback:
            return
        try:
            callback()
            logger.debug(f"Hotkey triggered: Ctrl+Shift+{letter.upper()}")
        except Exception as exc:
            logger.error(f"Hotkey callback failed for {letter}: {exc}")

    def _on_release(self, key: Any) -> None:
        self._pressed.discard(key)

    def _ctrl_shift_down(self) -> bool:
        ctrl_down = any(
            key in self._pressed
            for key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
        )
        shift_down = any(
            key in self._pressed
            for key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
        )
        return ctrl_down and shift_down

    @staticmethod
    def _key_letter(key: Any) -> str | None:
        char = getattr(key, "char", None)
        if not char:
            return None
        lowered = str(char).lower()
        return lowered if lowered in {"p", "m", "r", "h"} else None
