"""Prompt to link Vectorworks when no executable is configured."""

from __future__ import annotations

import os

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class VectorworksSetupDialog(QDialog):
    """Ask the user to locate Vectorworks.exe when auto-detection fails."""

    def __init__(
        self,
        browse_directory: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Link Vectorworks")
        self.setMinimumWidth(520)
        self._browse_directory = browse_directory or ""
        self._selected_path = ""

        layout = QVBoxLayout(self)
        intro = QLabel(
            "VectorTrack could not find Vectorworks automatically.\n\n"
            "Choose your Vectorworks executable (usually Vectorworks.exe inside a year "
            "folder under Program Files). VectorTrack uses this to detect open drawings "
            "and to locate Vectorworks Log.txt for history import."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("No executable selected")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        hint = QLabel(
            f"Typical location: {self._browse_directory or r'C:\\Program Files\\Vectorworks\\<year>'}"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox()
        self.link_btn = buttons.addButton("Link Vectorworks", QDialogButtonBox.ButtonRole.AcceptRole)
        self.link_btn.setEnabled(False)
        skip_btn = buttons.addButton("Skip for now", QDialogButtonBox.ButtonRole.RejectRole)
        self.link_btn.clicked.connect(self.accept)
        skip_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def selected_path(self) -> str:
        return self._selected_path

    def _browse(self) -> None:
        start_dir = self._browse_directory
        if self._selected_path:
            start_dir = os.path.dirname(self._selected_path)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Vectorworks executable",
            start_dir,
            "Executable (*.exe);;All files (*)",
        )
        if not file_path:
            return
        self._selected_path = file_path
        self.path_edit.setText(file_path)
        self.link_btn.setEnabled(True)
