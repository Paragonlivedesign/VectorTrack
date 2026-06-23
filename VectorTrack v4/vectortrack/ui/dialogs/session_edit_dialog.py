"""Edit an existing tracked/manual/adjustment session."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import (
    QDateTimeEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vectortrack.services.session_aggregator import UnifiedSession


class SessionEditDialog(QDialog):
    def __init__(self, session: UnifiedSession, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Session")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.file_input = QLineEdit(session.file_path)
        self.start_input = QDateTimeEdit()
        self.start_input.setCalendarPopup(True)
        self.start_input.setDateTime(session.start)
        self.end_input = QDateTimeEdit()
        self.end_input.setCalendarPopup(True)
        self.end_input.setDateTime(session.end)
        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0, 10000)
        self.rate_input.setDecimals(2)
        self.rate_input.setValue(session.hourly_rate)
        self.notes_input = QLineEdit(session.notes)

        form.addRow("File path", self.file_input)
        form.addRow("Start", self.start_input)
        form.addRow("End", self.end_input)
        form.addRow("Rate", self.rate_input)
        if session.source == "adjustment":
            form.addRow("Notes", self.notes_input)

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

    def values(self) -> dict[str, object]:
        return {
            "file_path": self.file_input.text().strip(),
            "start_time": self.start_input.dateTime().toPyDateTime(),
            "end_time": self.end_input.dateTime().toPyDateTime(),
            "hourly_rate": float(self.rate_input.value()),
            "notes": self.notes_input.text().strip(),
        }
