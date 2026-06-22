"""Windows startup registration helpers for VectorTrack."""

from __future__ import annotations

import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "VectorTrack"


def _executable_path() -> str:
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())
    return str((Path(__file__).resolve().parents[2] / "run.py").resolve())


def is_enabled() -> bool:
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            try:
                winreg.QueryValueEx(key, APP_NAME)
                return True
            except FileNotFoundError:
                return False
    except OSError:
        return False


def set_enabled(enabled: bool, exe_path: str | None = None) -> None:
    if not sys.platform.startswith("win"):
        return
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            target = exe_path or _executable_path()
            if target.endswith(".py"):
                command = f'"{sys.executable}" "{target}"'
            else:
                command = f'"{target}"'
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
            return
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
