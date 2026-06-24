"""Dialog to set hourly rate for a live open session."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class RateEditDialog(QDialog):
    def __init__(
        self,
        current_rate: float,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Session Rate")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0, 10000)
        self.rate_input.setDecimals(2)
        self.rate_input.setValue(float(current_rate))
        form.addRow("Hourly rate", self.rate_input)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def hourly_rate(self) -> float:
        return float(self.rate_input.value())
