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
        projects: list[tuple[str, str, float]],
        suggested_file: str = "",
        default_rate: float = 75.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._default_rate = float(default_rate)
        self._project_rates = {code: float(rate) for code, _label, rate in projects}
        self._rate_edited_manually = False
        self.setWindowTitle("Manual Time Entry")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.project_combo = QComboBox()
        for code, label, _rate in projects:
            self.project_combo.addItem(label, code)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
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
        self.rate_input.setValue(self._default_rate)
        self.rate_input.valueChanged.connect(self._on_rate_changed)
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

    def _on_rate_changed(self, _value: float) -> None:
        self._rate_edited_manually = True

    def _on_project_changed(self, _index: int) -> None:
        if self._rate_edited_manually:
            return
        project_code = str(self.project_combo.currentData() or "")
        rate = self._project_rates.get(project_code, self._default_rate)
        self.rate_input.blockSignals(True)
        self.rate_input.setValue(float(rate))
        self.rate_input.blockSignals(False)

    def values(self) -> dict[str, object]:
        return {
            "project_id": str(self.project_combo.currentData() or ""),
            "file_path": self.file_input.text().strip(),
            "start_time": self.start_input.dateTime().toPyDateTime(),
            "end_time": self.end_input.dateTime().toPyDateTime(),
            "hourly_rate": float(self.rate_input.value()),
        }
