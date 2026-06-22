"""Open-file tracking table widget."""

from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)


class OpenFilesTable(QTableWidget):
    assign_project_requested = pyqtSignal(str)
    manual_entry_requested = pyqtSignal(str)

    HEADERS = ["File", "Project", "Status", "Past", "Live", "Delta", "Rate", "Earned", "Actions"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setStretchLastSection(True)

    def set_rows(self, rows: Iterable[dict[str, object]]) -> None:
        self.setRowCount(0)
        for row_data in rows:
            row = self.rowCount()
            self.insertRow(row)
            file_path = str(row_data.get("file_path", ""))
            status = str(row_data.get("status", "Open"))
            values = [
                str(row_data.get("file_name", "")),
                str(row_data.get("project", "")),
                status,
                f'{float(row_data.get("past_hours", 0.0)):.2f}h',
                f'{float(row_data.get("live_hours", 0.0)):.2f}h',
                f'{float(row_data.get("delta_hours", 0.0)):+.2f}h',
                f'${float(row_data.get("rate", 0.0)):.2f}',
                f'${float(row_data.get("earned", 0.0)):.2f}',
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, file_path)
                self.setItem(row, col, item)

            actions = QWidget(self)
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            assign_btn = QPushButton("Assign")
            assign_btn.clicked.connect(lambda _checked=False, fp=file_path: self.assign_project_requested.emit(fp))
            entry_btn = QPushButton("Add Time")
            entry_btn.clicked.connect(lambda _checked=False, fp=file_path: self.manual_entry_requested.emit(fp))
            actions_layout.addWidget(assign_btn)
            actions_layout.addWidget(entry_btn)
            self.setCellWidget(row, 8, actions)

    def file_path_for_row(self, row: int) -> str:
        item = self.item(row, 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "")

