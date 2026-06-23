"""Top-level KPI strip for today/week/month/earned and active session timer."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from vectortrack.ui.formatting import format_hours_compact, format_timer_hours


class DashboardStrip(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)

        self._value_labels: dict[str, QLabel] = {}
        cards = [
            ("active", "Active Project"),
            ("today", "Today"),
            ("week", "This Week"),
            ("month", "This Month"),
            ("earned", "Earned"),
        ]
        for idx, (key, title) in enumerate(cards):
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            heading = QLabel(title)
            heading.setObjectName("muted")
            if key == "active":
                default = "—"
            elif key == "earned":
                default = "$0.00"
            else:
                default = "0.00h"
            value = QLabel(default)
            value.setStyleSheet("font-size: 18px; font-weight: 700;")
            card_layout.addWidget(heading)
            card_layout.addWidget(value)
            layout.addWidget(card, 0, idx)
            self._value_labels[key] = value

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
