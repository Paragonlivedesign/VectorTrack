"""History browser tab widget with filters and session table."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QBrush, QColor
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

from vectortrack.ui.layout_utils import configure_compact_table
from vectortrack.ui.theme import table_status_colors


class HistoryBrowser(QWidget):
    refresh_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        filters = QHBoxLayout()
        filters.setSpacing(6)
        self.project_filter = QComboBox()
        self.project_filter.addItem("All Projects", "")
        now = datetime.now()
        self.from_filter = QDateTimeEdit()
        self.from_filter.setCalendarPopup(True)
        self.from_filter.setDateTime(
            (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        )
        self.to_filter = QDateTimeEdit()
        self.to_filter.setCalendarPopup(True)
        self.to_filter.setDateTime(now.replace(hour=23, minute=59, second=59, microsecond=0))
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

        self.table = QTableWidget(0, 9, self)
        self.table.setHorizontalHeaderLabels(
            ["Start", "End", "Project", "File", "Machine", "Hours", "Rate", "Amount", "Status"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        configure_compact_table(
            self.table,
            stretch_column=3,
            content_columns=[0, 1, 2, 4, 5, 6, 7, 8],
        )
        layout.addWidget(self.table, 1)

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
                str(item.get("machine", "")),
                f'{float(item.get("hours", 0.0)):.2f}',
                f'${float(item.get("rate", 0.0)):.2f}',
                f'${float(item.get("amount", 0.0)):.2f}',
                str(item.get("status", "")),
            ]
            status = str(item.get("status", ""))
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if status == "Excluded":
                    bg, fg = table_status_colors("excluded")
                    cell.setBackground(QBrush(bg))
                    cell.setForeground(QBrush(fg))
                elif status == "Conflict":
                    bg, _fg = table_status_colors("conflict")
                    cell.setBackground(QBrush(bg))
                self.table.setItem(row, col, cell)
