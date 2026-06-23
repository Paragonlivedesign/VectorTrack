"""Quick dialog to create a billable project."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


class NewProjectDialog(QDialog):
    def __init__(self, default_rate: float = 75.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.client_name = QLineEdit()
        self.client_name.setPlaceholderText("Default")
        self.project_code = QLineEdit()
        self.project_code.setPlaceholderText("Optional")
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("Required")
        self.hourly_rate = QDoubleSpinBox()
        self.hourly_rate.setRange(0, 10000)
        self.hourly_rate.setDecimals(2)
        self.hourly_rate.setValue(default_rate)
        form.addRow("Client", self.client_name)
        form.addRow("Project Number (optional)", self.project_code)
        form.addRow("Project Name", self.project_name)
        form.addRow("Hourly Rate", self.hourly_rate)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict[str, object]:
        return {
            "client_name": self.client_name.text().strip(),
            "project_code": self.project_code.text().strip(),
            "project_name": self.project_name.text().strip(),
            "hourly_rate": float(self.hourly_rate.value()),
        }
