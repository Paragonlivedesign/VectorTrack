"""Billable project summary table with budget progress."""

from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import QItemSelection, QItemSelectionModel, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import QProgressBar, QTableWidget, QTableWidgetItem, QWidget

from vectortrack.budget import (
    BudgetType,
    ProjectBudget,
    budget_progress_percent,
    budget_usage,
    format_budget_display,
)
from vectortrack.ui.layout_utils import configure_compact_table
from vectortrack.ui.theme import table_status_colors


class ProjectSummaryTable(QTableWidget):
    view_sessions_requested = pyqtSignal(str)
    edit_project_requested = pyqtSignal(str)

    HEADERS = ["Project", "Rate", "Tracked", "Billable", "Budget", "Progress"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        configure_compact_table(
            self,
            stretch_column=0,
            content_columns=[1, 2, 3, 4],
            fixed_columns={5: 110},
        )
        self.cellDoubleClicked.connect(self._on_double_click)

    def set_rows(self, rows: Iterable[dict[str, object]]) -> None:
        selected_code = ""
        current_row = self.currentRow()
        if current_row >= 0:
            selected_code = self.project_code_for_row(current_row)
        self.setUpdatesEnabled(False)
        try:
            self.setRowCount(0)
            for data in rows:
                row = self.rowCount()
                self.insertRow(row)
                tracked = float(data.get("tracked_hours", 0.0))
                billable = float(data.get("billable", 0.0))
                budget_type = str(data.get("budget_type", BudgetType.NONE.value))
                budget_amount = float(data.get("budget_amount", 0.0))
                if budget_type == BudgetType.MONEY.value and budget_amount > 0:
                    budget = ProjectBudget(BudgetType.MONEY, budget_amount)
                elif budget_type == BudgetType.HOURS.value and budget_amount > 0:
                    budget = ProjectBudget(BudgetType.HOURS, budget_amount)
                else:
                    budget = ProjectBudget(BudgetType.NONE, 0.0)
                used, limit = budget_usage(
                    budget,
                    tracked_hours=tracked,
                    billable=billable,
                )
                progress_pct = budget_progress_percent(
                    budget,
                    tracked_hours=tracked,
                    billable=billable,
                )
                columns = [
                    str(data.get("project", "")),
                    f'${float(data.get("rate", 0.0)):.2f}',
                    f"{tracked:.2f}h",
                    f"${billable:.2f}",
                    format_budget_display(budget),
                ]
                for col, value in enumerate(columns):
                    item = QTableWidgetItem(value)
                    if col == 0:
                        item.setData(Qt.ItemDataRole.UserRole, str(data.get("project_code") or data.get("project", "")))
                    self.setItem(row, col, item)
                bar = QProgressBar(self)
                bar.setRange(0, 100)
                bar.setValue(progress_pct)
                bar.setFormat(f"{progress_pct}%")
                warning = limit > 0 and used >= (limit * 0.8)
                over_budget = limit > 0 and used > limit
                if over_budget:
                    bar.setStyleSheet("QProgressBar::chunk { background-color: #c44242; }")
                elif warning:
                    bar.setStyleSheet("QProgressBar::chunk { background-color: #d4a72c; }")
                else:
                    bar.setStyleSheet("QProgressBar::chunk { background-color: #2a9d5a; }")
                self.setCellWidget(row, 5, bar)
                self._style_budget_cells(
                    row,
                    warning=warning,
                    over_budget=over_budget,
                    money_budget=budget.budget_type == BudgetType.MONEY,
                )
        finally:
            self.setUpdatesEnabled(True)
        self._restore_selection(selected_code)

    def _restore_selection(self, project_code: str) -> None:
        if not project_code:
            return
        for row in range(self.rowCount()):
            if self.project_code_for_row(row) != project_code:
                continue
            selection = QItemSelection()
            last_col = self.columnCount() - 1
            selection.select(self.model().index(row, 0), self.model().index(row, last_col))
            model = self.selectionModel()
            if model is None:
                return
            model.select(
                selection,
                QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
            )
            return

    def project_code_for_row(self, row: int) -> str:
        item = self.item(row, 0)
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "")

    def _style_budget_cells(self, row: int, *, warning: bool, over_budget: bool, money_budget: bool) -> None:
        if over_budget:
            color, _ = table_status_colors("danger")
        elif warning:
            color, _ = table_status_colors("warning")
        else:
            return
        brush = QBrush(color)
        usage_col = 3 if money_budget else 2
        for col in (usage_col, 4):
            item = self.item(row, col)
            if item is not None:
                item.setBackground(brush)

    def _on_double_click(self, row: int, column: int) -> None:
        project_code = self.project_code_for_row(row)
        if not project_code:
            return
        if column == 0:
            self.edit_project_requested.emit(project_code)
            return
        self.view_sessions_requested.emit(project_code)

