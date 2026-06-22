"""Mini heads-up display window for quick tracking glance."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class HUDWindow(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("VectorTrack HUD")
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.resize(250, 100)
        layout = QVBoxLayout(self)
        self.file_label = QLabel("No active file")
        self.time_label = QLabel("0.00h")
        self.money_label = QLabel("$0.00")
        self.time_label.setStyleSheet("font-size: 22px; font-weight: 700;")
        self.money_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.file_label)
        layout.addWidget(self.time_label)
        layout.addWidget(self.money_label)

    def set_stats(self, file_name: str, hours: float, amount: float) -> None:
        self.file_label.setText(file_name or "No active file")
        self.time_label.setText(f"{hours:.2f}h")
        self.money_label.setText(f"${amount:.2f}")

