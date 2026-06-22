"""Assign an active file to a billable project."""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class ProjectAssignDialog(QDialog):
    def __init__(self, file_path: str, projects: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Assign Project")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"File: {file_path}"))
        self.project_combo = QComboBox()
        for project in projects:
            self.project_combo.addItem(project)
        layout.addWidget(self.project_combo)
        buttons = QHBoxLayout()
        assign_btn = QPushButton("Assign")
        assign_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(assign_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def selected_project(self) -> str:
        return self.project_combo.currentText().strip()

