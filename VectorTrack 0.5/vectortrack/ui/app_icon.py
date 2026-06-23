"""Resolve VectorTrack application icons for dev and frozen builds."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QStyle, QWidget


def _assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets"
    return Path(__file__).resolve().parents[2] / "assets"


def app_icon(parent: QWidget | None = None) -> QIcon:
    for name in ("vectortrack.ico", "vectortrack.png"):
        path = _assets_dir() / name
        if path.exists():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    if getattr(sys, "frozen", False):
        icon = QIcon(sys.executable)
        if not icon.isNull():
            return icon
    if parent is not None:
        return parent.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        return app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    return QIcon()
