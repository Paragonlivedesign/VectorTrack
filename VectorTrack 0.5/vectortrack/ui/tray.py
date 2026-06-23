"""System tray integration for VectorTrack."""

from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from vectortrack.ui.app_icon import app_icon


class VectorTrackTray(QSystemTrayIcon):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(app_icon(parent), parent)
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

