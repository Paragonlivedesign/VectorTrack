"""Billable project summary table with budget progress."""

from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import QProgressBar, QTableWidget, QTableWidgetItem, QWidget


class ProjectSummaryTable(QTableWidget):
    HEADERS = ["Project", "Rate", "Tracked", "Billable", "Budget", "Progress"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setStretchLastSection(True)

    def set_rows(self, rows: Iterable[dict[str, object]]) -> None:
        self.setRowCount(0)
        for data in rows:
            row = self.rowCount()
            self.insertRow(row)
            tracked = float(data.get("tracked_hours", 0.0))
            budget = float(data.get("budget_hours", 0.0))
            progress_pct = 0 if budget <= 0 else max(0, min(100, int((tracked / budget) * 100)))
            columns = [
                str(data.get("project", "")),
                f'${float(data.get("rate", 0.0)):.2f}',
                f"{tracked:.2f}h",
                f'${float(data.get("billable", 0.0)):.2f}',
                "N/A" if budget <= 0 else f"{budget:.2f}h",
            ]
            for col, value in enumerate(columns):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, str(data.get("project", "")))
                self.setItem(row, col, item)
            bar = QProgressBar(self)
            bar.setRange(0, 100)
            bar.setValue(progress_pct)
            bar.setFormat(f"{progress_pct}%")
            warning = budget > 0 and tracked >= (budget * 0.8)
            over_budget = budget > 0 and tracked > budget
            if budget > 0 and tracked > budget:
                bar.setStyleSheet("QProgressBar::chunk { background-color: #c44242; }")
            elif budget > 0 and tracked >= (budget * 0.8):
                bar.setStyleSheet("QProgressBar::chunk { background-color: #d4a72c; }")
            else:
                bar.setStyleSheet("QProgressBar::chunk { background-color: #2a9d5a; }")
            self.setCellWidget(row, 5, bar)
            self._style_budget_cells(row, warning=warning, over_budget=over_budget)

    def project_code_for_row(self, row: int) -> str:
        item = self.item(row, 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "")

    def _style_budget_cells(self, row: int, *, warning: bool, over_budget: bool) -> None:
        color = None
        if over_budget:
            color = QColor("#f2b8b5")
        elif warning:
            color = QColor("#f6deb2")
        if color is None:
            return
        brush = QBrush(color)
        for col in (2, 4):
            item = self.item(row, col)
            if item is not None:
                item.setBackground(brush)

