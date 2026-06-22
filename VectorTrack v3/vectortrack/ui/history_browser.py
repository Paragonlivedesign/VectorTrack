"""History browser tab widget with filters and session table."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class HistoryBrowser(QWidget):
    refresh_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        filters = QHBoxLayout()
        self.project_filter = QComboBox()
        self.project_filter.addItem("All Projects", "")
        self.from_filter = QDateTimeEdit()
        self.from_filter.setCalendarPopup(True)
        self.from_filter.setDateTime(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
        self.to_filter = QDateTimeEdit()
        self.to_filter.setCalendarPopup(True)
        self.to_filter.setDateTime(datetime.now())
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        filters.addWidget(QLabel("Project"))
        filters.addWidget(self.project_filter)
        filters.addWidget(QLabel("From"))
        filters.addWidget(self.from_filter)
        filters.addWidget(QLabel("To"))
        filters.addWidget(self.to_filter)
        filters.addWidget(refresh_btn)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 7, self)
        self.table.setHorizontalHeaderLabels(
            ["Start", "End", "Project", "File", "Hours", "Rate", "Amount"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

    def set_project_options(self, project_codes: Iterable[str]) -> None:
        current = self.project_filter.currentData()
        self.project_filter.blockSignals(True)
        self.project_filter.clear()
        self.project_filter.addItem("All Projects", "")
        for code in project_codes:
            self.project_filter.addItem(code, code)
        idx = max(0, self.project_filter.findData(current))
        self.project_filter.setCurrentIndex(idx)
        self.project_filter.blockSignals(False)

    def selected_project(self) -> str:
        return str(self.project_filter.currentData() or "")

    def set_rows(self, rows: Iterable[dict[str, object]]) -> None:
        self.table.setRowCount(0)
        for item in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                str(item.get("start", "")),
                str(item.get("end", "")),
                str(item.get("project", "")),
                str(item.get("file", "")),
                f'{float(item.get("hours", 0.0)):.2f}',
                f'${float(item.get("rate", 0.0)):.2f}',
                f'${float(item.get("amount", 0.0)):.2f}',
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))

