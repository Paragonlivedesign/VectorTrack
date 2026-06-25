"""Month heatmap widget for daily tracked hours."""

from __future__ import annotations

import calendar
from datetime import date, datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vectortrack.ui.layout_utils import configure_compact_table, scale_px
from vectortrack.ui.theme import current_tokens, current_theme_mode, table_status_colors


class HeatmapWidget(QWidget):
    """Calendar heatmap where each day cell shows tracked hours intensity."""

    day_clicked = pyqtSignal(date)
    view_in_history_requested = pyqtSignal(date)

    def __init__(self, parent: QWidget | None = None, *, show_day_details: bool = True) -> None:
        super().__init__(parent)
        self._show_day_details = show_day_details
        self._current_month = date.today().replace(day=1)
        self._hours_by_day: dict[date, float] = {}
        self._selected_day: date | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        calendar_panel = QWidget()
        calendar_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        calendar_layout = QVBoxLayout(calendar_panel)
        calendar_layout.setContentsMargins(0, 0, 0, 0)
        calendar_layout.setSpacing(4)

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
        calendar_layout.addLayout(header)

        weekday_header = QGridLayout()
        weekday_header.setHorizontalSpacing(0)
        weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for idx, name in enumerate(weekday_names):
            label = QLabel(name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setObjectName("muted")
            weekday_header.addWidget(label, 0, idx)
        calendar_layout.addLayout(weekday_header)

        self.table = QTableWidget(6, 7, self)
        row_height = scale_px(34)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(row_height)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(row_height * 6 + scale_px(2))
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemClicked.connect(self._on_item_clicked)
        calendar_layout.addWidget(self.table)

        if self._show_day_details:
            splitter = QSplitter(Qt.Orientation.Vertical)
            splitter.addWidget(calendar_panel)
            splitter.addWidget(self._build_details_panel())
            splitter.setStretchFactor(0, 0)
            splitter.setStretchFactor(1, 1)
            splitter.setSizes([scale_px(290), scale_px(360)])
            root.addWidget(splitter, 1)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            root.addWidget(calendar_panel)

        self._render_month()

    def _build_details_panel(self) -> QGroupBox:
        self.details_group = QGroupBox("Day Details")
        layout = QVBoxLayout(self.details_group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        self.details_summary = QLabel("Click a date to see sessions for that day.")
        self.details_summary.setObjectName("muted")
        self.details_summary.setWordWrap(True)
        header_row.addWidget(self.details_summary, 1)
        self.view_history_btn = QPushButton("View in History")
        self.view_history_btn.setEnabled(False)
        self.view_history_btn.clicked.connect(self._emit_view_in_history)
        header_row.addWidget(self.view_history_btn)
        layout.addLayout(header_row)

        self.details_table = QTableWidget(0, 6)
        self.details_table.setHorizontalHeaderLabels(
            ["Start", "End", "Project", "File", "Hours", "Amount"]
        )
        self.details_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.details_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        configure_compact_table(
            self.details_table,
            stretch_column=3,
            content_columns=[0, 1, 2, 4, 5],
        )
        layout.addWidget(self.details_table, 1)
        return self.details_group

    def set_day_values(self, values: dict[date, float]) -> None:
        self._hours_by_day = dict(values)
        self._render_month()
        if self._selected_day is not None:
            self._highlight_selected_day()

    def set_month(self, year: int, month: int) -> None:
        self._current_month = date(year, month, 1)
        self._render_month()

    def show_day_details(self, day: date, rows: list[dict[str, object]]) -> None:
        if not self._show_day_details:
            return
        self._selected_day = day
        self._highlight_selected_day()

        total_hours = sum(float(row.get("hours", 0.0) or 0.0) for row in rows)
        total_amount = sum(float(row.get("amount", 0.0) or 0.0) for row in rows)
        heatmap_hours = float(self._hours_by_day.get(day, 0.0))
        self.details_group.setTitle(day.strftime("%A, %B %d, %Y"))

        if rows:
            self.details_summary.setText(
                f"{len(rows)} entr{'y' if len(rows) == 1 else 'ies'} · "
                f"{total_hours:.2f}h tracked · ${total_amount:.2f} billable"
            )
        else:
            summary = f"No tracked sessions on this date."
            if heatmap_hours > 0:
                summary = f"{heatmap_hours:.2f}h recorded on the heatmap, but no session rows match this date."
            self.details_summary.setText(summary)

        self.details_table.setRowCount(0)
        for item in rows:
            row = self.details_table.rowCount()
            self.details_table.insertRow(row)
            columns = [
                str(item.get("start", "")),
                str(item.get("end", "")),
                str(item.get("project", "")),
                str(item.get("file", "")),
                f'{float(item.get("hours", 0.0) or 0.0):.2f}h',
                f'${float(item.get("amount", 0.0) or 0.0):.2f}',
            ]
            for col, value in enumerate(columns):
                self.details_table.setItem(row, col, QTableWidgetItem(value))

        self.view_history_btn.setEnabled(True)

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
        max_hours = max(
            (hours for d, hours in self._hours_by_day.items() if d.month == self._current_month.month),
            default=0.0,
        )

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
            if self._selected_day == day:
                tokens = current_tokens()
                item.setForeground(QColor(tokens["accent_text"]))
                item.setBackground(QColor(tokens["accent"]))
            self.table.setItem(row, col, item)

    def _highlight_selected_day(self) -> None:
        if self._selected_day is None:
            return
        if (
            self._selected_day.month != self._current_month.month
            or self._selected_day.year != self._current_month.year
        ):
            return
        self._render_month()

    @staticmethod
    def _cell_color(hours: float, max_hours: float) -> QColor:
        if hours <= 0:
            bg, _ = table_status_colors("heatmap_empty")
            return bg
        if max_hours <= 0:
            max_hours = 1.0
        intensity = min(1.0, hours / max_hours)
        if current_theme_mode() == "dark":
            value = int(72 + intensity * 128)
            return QColor(value, value, value)
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

    def _emit_view_in_history(self) -> None:
        if self._selected_day is not None:
            self.view_in_history_requested.emit(self._selected_day)
