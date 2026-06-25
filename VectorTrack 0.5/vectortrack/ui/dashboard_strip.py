"""Top-level KPI strip for today/week/month/earned and active session timer."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from vectortrack.ui.formatting import format_hours_compact, format_timer_hours
from vectortrack.ui.layout_utils import scale_px


class DashboardStrip(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(scale_px(8))

        self._value_labels: dict[str, QLabel] = {}
        cards = [
            ("active", "Active Project"),
            ("today", "Today"),
            ("week", "This Week"),
            ("month", "This Month"),
            ("earned", "Earned"),
        ]
        card_width = scale_px(168)
        for key, title in cards:
            card = QFrame()
            card.setObjectName("card")
            card.setMaximumWidth(card_width)
            card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(scale_px(10), scale_px(8), scale_px(10), scale_px(8))
            card_layout.setSpacing(scale_px(2))
            heading = QLabel(title)
            heading.setObjectName("muted")
            if key == "active":
                default = "—"
            elif key == "earned":
                default = "$0.00"
            else:
                default = "0.00h"
            value = QLabel(default)
            value.setObjectName("dashboardValue")
            card_layout.addWidget(heading)
            card_layout.addWidget(value)
            layout.addWidget(card)
            self._value_labels[key] = value
        layout.addStretch()

    def set_metrics(
        self,
        *,
        today_hours: float,
        week_hours: float,
        month_hours: float,
        earned: float,
        active_project: str | None = None,
        active_live_hours: float = 0.0,
        active_is_tracking: bool = False,
    ) -> None:
        if active_project:
            timer = format_timer_hours(active_live_hours)
            prefix = "▶" if active_is_tracking else "⏸"
            self._value_labels["active"].setText(f"{prefix} {timer}")
            self._value_labels["active"].setToolTip(active_project)
        else:
            self._value_labels["active"].setText("—")
            self._value_labels["active"].setToolTip("")
        self._value_labels["today"].setText(format_hours_compact(today_hours))
        self._value_labels["week"].setText(format_hours_compact(week_hours))
        self._value_labels["month"].setText(format_hours_compact(month_hours))
        self._value_labels["earned"].setText(f"${earned:,.2f}")
