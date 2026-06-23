"""Open-file tracking table widget."""

from __future__ import annotations

from typing import Iterable, List

from PyQt6.QtCore import QItemSelection, QItemSelectionModel, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from vectortrack.ui.formatting import format_hours_compact, format_timer_hours


class OpenFilesTable(QTableWidget):
    assign_project_requested = pyqtSignal(str)
    assign_projects_requested = pyqtSignal(list)
    edit_project_requested = pyqtSignal(str)
    manual_entry_requested = pyqtSignal(str)
    view_sessions_requested = pyqtSignal(str)
    resume_tracking_requested = pyqtSignal(str)

    HEADERS = ["File", "Project", "Status", "Past", "Live", "Delta", "Rate", "Earned", "Actions"]
    LIVE_COLUMN = 4
    STATUS_COLUMN = 2
    ROLE_FILE_PATH = Qt.ItemDataRole.UserRole
    ROLE_ROW_KIND = Qt.ItemDataRole.UserRole + 1
    ROLE_PROJECT_CODE = Qt.ItemDataRole.UserRole + 2

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setStretchLastSection(True)
        self.cellDoubleClicked.connect(self._on_double_click)
        self.cellClicked.connect(self._on_cell_clicked)

    def update_rows(self, rows: Iterable[dict[str, object]]) -> None:
        rows_list = list(rows)
        new_paths = [str(row.get("file_path", "")) for row in rows_list]
        current_paths = [self.file_path_for_row(row_index) for row_index in range(self.rowCount())]
        if new_paths != current_paths:
            self.set_rows(rows_list)
            return

        for row_index, row_data in enumerate(rows_list):
            self._apply_row_data(row_index, row_data, rebuild_actions=False)

    def set_rows(self, rows: Iterable[dict[str, object]]) -> None:
        rows_list = list(rows)
        selected_paths = set(self.selected_file_paths())
        self.setUpdatesEnabled(False)
        try:
            self.setRowCount(0)
            for row_data in rows_list:
                row = self.rowCount()
                self.insertRow(row)
                self._apply_row_data(row, row_data, rebuild_actions=True)
        finally:
            self.setUpdatesEnabled(True)
        self._restore_selection(selected_paths)

    def _apply_row_data(self, row: int, row_data: dict[str, object], *, rebuild_actions: bool) -> None:
        file_path = str(row_data.get("file_path", ""))
        row_kind = str(row_data.get("row_kind", "open"))
        status = str(row_data.get("status", "Open"))
        past_hours = float(row_data.get("past_hours", 0.0))
        live_hours = float(row_data.get("live_hours", 0.0))
        delta_hours = float(row_data.get("delta_hours", 0.0))
        is_tracking = bool(row_data.get("is_tracking", False))
        live_text = format_timer_hours(live_hours)
        if row_kind == "active":
            live_text = f"{'▶' if is_tracking else '⏸'} {live_text}"
        values = [
            str(row_data.get("file_name", "")),
            str(row_data.get("project", "")),
            status,
            format_hours_compact(past_hours),
            live_text,
            f"{delta_hours:+.2f}h",
            f"${float(row_data.get('rate', 0.0)):.2f}",
            f"${float(row_data.get('earned', 0.0)):.2f}",
        ]
        for col, value in enumerate(values):
            item = self.item(row, col)
            if item is None:
                item = QTableWidgetItem(value)
                self.setItem(row, col, item)
            else:
                item.setText(value)
            if col == 0:
                item.setData(self.ROLE_FILE_PATH, file_path)
                item.setData(self.ROLE_ROW_KIND, row_kind)
                font = QFont()
                font.setBold(row_kind == "active")
                item.setFont(font)
            elif col == 1:
                item.setData(self.ROLE_PROJECT_CODE, str(row_data.get("project_code", "")))
            elif col == self.LIVE_COLUMN and row_kind == "active" and not is_tracking:
                item.setToolTip("Click to resume tracking for this file")
            elif col == self.LIVE_COLUMN:
                item.setToolTip("")
            self._style_item(item, row_kind)

        if rebuild_actions or self.cellWidget(row, 8) is None:
            actions = QWidget(self)
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            assign_btn = QPushButton("Assign")
            assign_btn.clicked.connect(lambda _checked=False, fp=file_path: self.assign_project_requested.emit(fp))
            sessions_btn = QPushButton("Sessions")
            sessions_btn.clicked.connect(lambda _checked=False, fp=file_path: self.view_sessions_requested.emit(fp))
            entry_btn = QPushButton("Add Time")
            entry_btn.clicked.connect(lambda _checked=False, fp=file_path: self.manual_entry_requested.emit(fp))
            actions_layout.addWidget(assign_btn)
            actions_layout.addWidget(sessions_btn)
            actions_layout.addWidget(entry_btn)
            self.setCellWidget(row, 8, actions)

    def _restore_selection(self, selected_paths: set[str]) -> None:
        if not selected_paths:
            return
        selection = QItemSelection()
        last_col = self.columnCount() - 1
        for row in range(self.rowCount()):
            file_path = self.file_path_for_row(row)
            if file_path not in selected_paths:
                continue
            selection.select(self.model().index(row, 0), self.model().index(row, last_col))
        if selection.isEmpty():
            return
        model = self.selectionModel()
        if model is None:
            return
        model.select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows)

    @staticmethod
    def _style_item(item: QTableWidgetItem, row_kind: str) -> None:
        if row_kind == "active":
            item.setBackground(QBrush(QColor("#e8f4ff")))
            item.setForeground(QBrush(QColor("#1a1a1a")))
            return
        if row_kind in {"open", "recent"}:
            item.setBackground(QBrush(QColor("#f0f0f0")))
            item.setForeground(QBrush(QColor("#777777")))

    def selected_file_paths(self) -> List[str]:
        paths: List[str] = []
        seen = set()
        for item in self.selectedItems():
            if item.column() != 0:
                continue
            file_path = str(item.data(self.ROLE_FILE_PATH) or "")
            if file_path and file_path not in seen:
                seen.add(file_path)
                paths.append(file_path)
        return paths

    def _on_cell_clicked(self, row: int, column: int) -> None:
        if column not in (self.STATUS_COLUMN, self.LIVE_COLUMN):
            return
        item = self.item(row, 0)
        if item is None or str(item.data(self.ROLE_ROW_KIND) or "") != "active":
            return
        file_path = self.file_path_for_row(row)
        if file_path:
            self.resume_tracking_requested.emit(file_path)

    def _on_double_click(self, row: int, column: int) -> None:
        file_path = self.file_path_for_row(row)
        if not file_path:
            return
        if column == 1:
            self.edit_project_requested.emit(file_path)
            return
        self.view_sessions_requested.emit(file_path)

    def file_path_for_row(self, row: int) -> str:
        item = self.item(row, 0)
        if item is None:
            return ""
        return str(item.data(self.ROLE_FILE_PATH) or "")

    def project_code_for_row(self, row: int) -> str:
        item = self.item(row, 1)
        if item is None:
            return ""
        return str(item.data(self.ROLE_PROJECT_CODE) or "")
