"""Dialog for manual time entry."""

from __future__ import annotations

from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QComboBox,
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


class ManualEntryDialog(QDialog):
    def __init__(
        self,
        projects: list[str],
        suggested_file: str = "",
        default_rate: float = 75.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Manual Time Entry")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.project_combo = QComboBox()
        for project in projects:
            self.project_combo.addItem(project)
        self.file_input = QLineEdit(suggested_file)
        self.start_input = QDateTimeEdit()
        self.start_input.setCalendarPopup(True)
        now = datetime.now()
        self.start_input.setDateTime(now - timedelta(hours=1))
        self.end_input = QDateTimeEdit()
        self.end_input.setCalendarPopup(True)
        self.end_input.setDateTime(now)
        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0, 10000)
        self.rate_input.setDecimals(2)
        self.rate_input.setValue(default_rate)
        form.addRow("Project", self.project_combo)
        form.addRow("File path", self.file_input)
        form.addRow("Start", self.start_input)
        form.addRow("End", self.end_input)
        form.addRow("Rate", self.rate_input)
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
            "project_id": self.project_combo.currentText().strip(),
            "file_path": self.file_input.text().strip(),
            "start_time": self.start_input.dateTime().toPyDateTime(),
            "end_time": self.end_input.dateTime().toPyDateTime(),
            "hourly_rate": float(self.rate_input.value()),
        }

