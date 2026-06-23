"""Assign one or more active files to a billable project."""

from __future__ import annotations

import os

from PyQt6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


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
        self.setMinimumWidth(420)
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

    @property
    def file_paths(self) -> list[str]:
        return list(self._file_paths)

    def selected_project(self) -> str:
        return str(self.project_combo.currentData() or "")
