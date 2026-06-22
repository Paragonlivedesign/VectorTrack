"""System tray integration for VectorTrack."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QStyle, QSystemTrayIcon, QWidget


def _tray_icon(parent: QWidget) -> QIcon:
    candidates = [
        Path(__file__).resolve().parents[2] / "assets" / "vectortrack.ico",
        Path(__file__).resolve().parents[2] / "assets" / "vectortrack.png",
    ]
    for path in candidates:
        if path.exists():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    return parent.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)


class VectorTrackTray(QSystemTrayIcon):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(_tray_icon(parent), parent)
        self.parent_window = parent
        menu = QMenu(parent)
        show_action = QAction("Show", self)
        hide_action = QAction("Hide", self)
        quit_action = QAction("Quit", self)
        show_action.triggered.connect(self._show_main)
        hide_action.triggered.connect(parent.hide)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _show_main(self) -> None:
        self.parent_window.showNormal()
        self.parent_window.raise_()
        self.parent_window.activateWindow()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_main()

    def _quit_app(self) -> None:
        if hasattr(self.parent_window, "_quit_app"):
            self.parent_window._quit_app()  # type: ignore[attr-defined]
            return
        self.parent_window.close()

