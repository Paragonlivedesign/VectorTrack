"""Top-level KPI strip for today/week/month/earned."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget


class DashboardStrip(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)

        self._value_labels: dict[str, QLabel] = {}
        cards = [
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
            value = QLabel("0.00h" if key != "earned" else "$0.00")
            value.setStyleSheet("font-size: 18px; font-weight: 700;")
            card_layout.addWidget(heading)
            card_layout.addWidget(value)
            layout.addWidget(card, 0, idx)
            self._value_labels[key] = value

    def set_metrics(self, *, today_hours: float, week_hours: float, month_hours: float, earned: float) -> None:
        self._value_labels["today"].setText(f"{today_hours:.2f}h")
        self._value_labels["week"].setText(f"{week_hours:.2f}h")
        self._value_labels["month"].setText(f"{month_hours:.2f}h")
        self._value_labels["earned"].setText(f"${earned:,.2f}")

