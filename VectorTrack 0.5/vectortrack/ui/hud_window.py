"""Mini heads-up display window for quick tracking glance."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from vectortrack.ui.formatting import format_timer_hours


class HUDWindow(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("VectorTrack HUD")
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(250, 110)
        self._move_to_default_corner()
        layout = QVBoxLayout(self)
        self.file_label = QLabel("No active file")
        self.time_label = QLabel("0:00")
        self.status_label = QLabel("")
        self.money_label = QLabel("$0.00")
        self.time_label.setStyleSheet("font-size: 22px; font-weight: 700;")
        self.status_label.setObjectName("muted")
        self.money_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.file_label)
        layout.addWidget(self.time_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.money_label)

    def set_stats(
        self,
        file_name: str,
        hours: float,
        amount: float,
        *,
        is_tracking: bool = False,
        tracking_status: str = "tracking",
        project_name: str | None = None,
    ) -> None:
        self.file_label.setText(file_name or "No active file")
        prefix = "▶" if is_tracking else "⏸"
        self.time_label.setText(f"{prefix} {format_timer_hours(hours)}")
        if is_tracking:
            self.status_label.setText("Tracking")
        elif tracking_status == "paused":
            self.status_label.setText("Paused")
        elif tracking_status == "idle":
            self.status_label.setText("Idle")
        elif file_name and file_name != "No active file":
            self.status_label.setText("Paused")
        else:
            self.status_label.setText("")
        if project_name:
            self.file_label.setToolTip(f"Project: {project_name}")
        else:
            self.file_label.setToolTip("")
        self.money_label.setText(f"${amount:.2f}")

    def _move_to_default_corner(self) -> None:
        from PyQt6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        self.move(geometry.right() - self.width() - 16, geometry.top() + 16)
