"""System tray integration for VectorTrack."""

from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from vectortrack.ui.app_icon import TrayStatus, tray_icon


class VectorTrackTray(QSystemTrayIcon):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(tray_icon(parent), parent)
        self.parent_window = parent
        self._status: TrayStatus = "inactive"
        menu = QMenu(parent)
        self.pause_action = QAction("Pause Tracking", self)
        show_action = QAction("Show", self)
        hide_action = QAction("Hide", self)
        quit_action = QAction("Quit", self)
        self.pause_action.triggered.connect(self._toggle_pause)
        show_action.triggered.connect(self._show_main)
        hide_action.triggered.connect(parent.hide)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(self.pause_action)
        menu.addSeparator()
        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def set_tracking_status(self, status: TrayStatus) -> None:
        if status == self._status:
            return
        self._status = status
        self.setIcon(tray_icon(self.parent_window, status))
        if status == "tracking":
            self.setToolTip("VectorTrack - Tracking")
        elif status == "idle":
            self.setToolTip("VectorTrack - Idle")
        elif status == "paused":
            self.setToolTip("VectorTrack - Paused")
        else:
            self.setToolTip("VectorTrack")

    def set_paused(self, paused: bool) -> None:
        self.pause_action.setText("Resume Tracking" if paused else "Pause Tracking")

    def _toggle_pause(self) -> None:
        toggle = getattr(self.parent_window, "_toggle_pause_from_tray", None)
        if callable(toggle):
            toggle()

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
