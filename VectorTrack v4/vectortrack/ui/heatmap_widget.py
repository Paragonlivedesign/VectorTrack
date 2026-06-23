"""Month heatmap widget for daily tracked hours."""

from __future__ import annotations

import calendar
from datetime import date, datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class HeatmapWidget(QWidget):
    """Simple calendar heatmap where each day cell shows tracked hours intensity."""

    day_clicked = pyqtSignal(date)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_month = date.today().replace(day=1)
        self._hours_by_day: dict[date, float] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self.prev_btn = QPushButton("<")
        self.prev_btn.clicked.connect(self._prev_month)
        self.next_btn = QPushButton(">")
        self.next_btn.clicked.connect(self._next_month)
        self.month_label = QLabel("")
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.prev_btn)
        header.addWidget(self.month_label, 1)
        header.addWidget(self.next_btn)
        root.addLayout(header)

        self.table = QTableWidget(6, 7, self)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemClicked.connect(self._on_item_clicked)

        weekday_header = QGridLayout()
        weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for idx, name in enumerate(weekday_names):
            label = QLabel(name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            weekday_header.addWidget(label, 0, idx)
        root.addLayout(weekday_header)
        root.addWidget(self.table)

        self._render_month()

    def set_day_values(self, values: dict[date, float]) -> None:
        self._hours_by_day = dict(values)
        self._render_month()

    def set_month(self, year: int, month: int) -> None:
        self._current_month = date(year, month, 1)
        self._render_month()

    def _prev_month(self) -> None:
        month = self._current_month.month - 1
        year = self._current_month.year
        if month == 0:
            month = 12
            year -= 1
        self._current_month = date(year, month, 1)
        self._render_month()

    def _next_month(self) -> None:
        month = self._current_month.month + 1
        year = self._current_month.year
        if month == 13:
            month = 1
            year += 1
        self._current_month = date(year, month, 1)
        self._render_month()

    def _render_month(self) -> None:
        self.table.clearContents()
        self.month_label.setText(self._current_month.strftime("%B %Y"))
        cal = calendar.Calendar(firstweekday=0)
        month_days = list(cal.itermonthdates(self._current_month.year, self._current_month.month))
        max_hours = max((hours for d, hours in self._hours_by_day.items() if d.month == self._current_month.month), default=0.0)

        for index, day in enumerate(month_days[:42]):
            row = index // 7
            col = index % 7
            if day.month != self._current_month.month:
                item = QTableWidgetItem("")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.table.setItem(row, col, item)
                continue
            hours = float(self._hours_by_day.get(day, 0.0))
            item = QTableWidgetItem(f"{day.day}\n{hours:.1f}h" if hours > 0 else str(day.day))
            item.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            item.setData(Qt.ItemDataRole.UserRole, day.isoformat())
            item.setBackground(self._cell_color(hours, max_hours))
            self.table.setItem(row, col, item)

    @staticmethod
    def _cell_color(hours: float, max_hours: float) -> QColor:
        if hours <= 0:
            return QColor("#2f2f2f")
        if max_hours <= 0:
            max_hours = 1.0
        intensity = min(1.0, hours / max_hours)
        red = int(50 + (1.0 - intensity) * 120)
        green = int(110 + intensity * 120)
        blue = int(50 + (1.0 - intensity) * 90)
        return QColor(red, green, blue)

    def _on_item_clicked(self, item: QTableWidgetItem) -> None:
        raw = item.data(Qt.ItemDataRole.UserRole)
        if not raw:
            return
        clicked = datetime.fromisoformat(str(raw)).date()
        self.day_clicked.emit(clicked)
