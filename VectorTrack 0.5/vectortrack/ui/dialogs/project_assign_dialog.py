"""Assign one or more active files to a billable project."""

from __future__ import annotations

import os

from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from vectortrack.db.repository import Repository


class ProjectAssignDialog(QDialog):
    def __init__(
        self,
        file_paths: list[str],
        projects: list[tuple[str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._file_paths = [path for path in file_paths if path]
        self.setWindowTitle("Assign Project")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)

        if len(self._file_paths) == 1:
            layout.addWidget(QLabel(f"File: {self._file_paths[0]}"))
        else:
            layout.addWidget(QLabel(f"{len(self._file_paths)} files selected:"))
            for file_path in self._file_paths[:8]:
                layout.addWidget(QLabel(f"  • {os.path.basename(file_path)}"))
            if len(self._file_paths) > 8:
                layout.addWidget(QLabel(f"  … and {len(self._file_paths) - 8} more"))

        self.project_combo = QComboBox()
        for code, label in projects:
            self.project_combo.addItem(label, code)
        layout.addWidget(QLabel("Project"))
        layout.addWidget(self.project_combo)

        layout.addWidget(QLabel("Rate on assignment"))
        self.rate_group = QButtonGroup(self)
        self.use_project_rate = QRadioButton("Use project rate")
        self.keep_current_rate = QRadioButton("Keep current rate")
        self.split_at_assignment = QRadioButton("Split at assignment (prior time keeps current rate)")
        self.use_project_rate.setChecked(True)
        for button in (self.use_project_rate, self.keep_current_rate, self.split_at_assignment):
            self.rate_group.addButton(button)
            layout.addWidget(button)

        buttons = QHBoxLayout()
        assign_btn = QPushButton("Assign")
        assign_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(assign_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    @property
    def file_paths(self) -> list[str]:
        return list(self._file_paths)

    def selected_project(self) -> str:
        return str(self.project_combo.currentData() or "")

    def selected_rate_strategy(self) -> str:
        if self.keep_current_rate.isChecked():
            return Repository.RATE_STRATEGY_KEEP
        if self.split_at_assignment.isChecked():
            return Repository.RATE_STRATEGY_SPLIT
        return Repository.RATE_STRATEGY_PROJECT
