"""Prompt to link Vectorworks Log.txt when logging is not configured."""

from __future__ import annotations

import os
import sys

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
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

from vectortrack.log_parser import VW_LOG_TIME_PREFERENCE_HELP, vectorworks_log_roaming_dir


class VectorworksLogSetupDialog(QDialog):
    """Ask the user to enable VW logging and locate Vectorworks Log.txt."""

    def __init__(
        self,
        expected_log_path: str = "",
        browse_directory: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Vectorworks Log")
        self.setMinimumWidth(560)
        self._expected_log_path = expected_log_path or ""
        self._browse_directory = browse_directory or vectorworks_log_roaming_dir()
        self._selected_path = ""

        layout = QVBoxLayout(self)
        intro = QLabel(
            "VectorTrack could not find Vectorworks Log.txt for history import.\n\n"
            f"{VW_LOG_TIME_PREFERENCE_HELP}\n\n"
            "After logging is enabled, open and close a drawing in Vectorworks once so "
            "the log file is created. Then link the log below (or browse to it manually)."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        if self._expected_log_path:
            expected = QLabel(f"Expected location:\n{self._expected_log_path}")
            expected.setWordWrap(True)
            layout.addWidget(expected)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("No log file selected")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        folder_row = QHBoxLayout()
        open_folder_btn = QPushButton("Open Log Folder")
        open_folder_btn.clicked.connect(self._open_log_folder)
        folder_row.addWidget(open_folder_btn)
        folder_row.addStretch()
        layout.addLayout(folder_row)

        buttons = QDialogButtonBox()
        self.link_btn = buttons.addButton("Link Log File", QDialogButtonBox.ButtonRole.AcceptRole)
        self.link_btn.setEnabled(False)
        skip_btn = buttons.addButton("Skip for now", QDialogButtonBox.ButtonRole.RejectRole)
        self.link_btn.clicked.connect(self.accept)
        skip_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

        if self._expected_log_path and os.path.isfile(self._expected_log_path):
            self._selected_path = self._expected_log_path
            self.path_edit.setText(self._expected_log_path)
            self.link_btn.setEnabled(True)

    @property
    def selected_path(self) -> str:
        return self._selected_path

    def _browse(self) -> None:
        start_dir = self._browse_directory
        if self._selected_path:
            start_dir = os.path.dirname(self._selected_path)
        elif self._expected_log_path:
            start_dir = os.path.dirname(self._expected_log_path)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Vectorworks log",
            start_dir,
            "Log files (*.log *.txt);;All files (*)",
        )
        if not file_path:
            return
        self._selected_path = file_path
        self.path_edit.setText(file_path)
        self.link_btn.setEnabled(True)

    def _open_log_folder(self) -> None:
        folder = self._browse_directory
        if self._expected_log_path:
            folder = os.path.dirname(self._expected_log_path)
        if not folder or not os.path.isdir(folder):
            folder = vectorworks_log_roaming_dir()
        if not os.path.isdir(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError:
                pass
        if not os.path.isdir(folder):
            return
        norm = os.path.normpath(folder)
        if sys.platform == "win32":
            os.startfile(norm)  # type: ignore[attr-defined]
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(norm))
