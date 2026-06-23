"""Bug report helper dialog."""

from __future__ import annotations

from urllib.parse import quote

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from vectortrack import config


class BugReportDialog(QDialog):
    SUPPORT_EMAIL = "Info@paragonlivedesign.com"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Report a Bug")
        self.setMinimumSize(560, 360)

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.subject_edit = QLineEdit("VectorTrack Bug Report")
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText("Describe what happened and how to reproduce it.")
        self.attach_logs_check = QCheckBox("Include logs path in email body")
        self.attach_logs_check.setChecked(True)
        form.addRow("Subject", self.subject_edit)
        form.addRow("Details", self.body_edit)
        form.addRow("", self.attach_logs_check)
        root.addLayout(form)

        buttons = QHBoxLayout()
        send_btn = QPushButton("Open Email App")
        send_btn.clicked.connect(self._open_mailto)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(send_btn)
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        root.addLayout(buttons)

    def _open_mailto(self) -> None:
        subject = self.subject_edit.text().strip() or "VectorTrack Bug Report"
        body = self.body_edit.toPlainText().strip()
        if self.attach_logs_check.isChecked():
            logs_dir = config.logs_dir()
            body = f"{body}\n\nLogs folder:\n{logs_dir}\n(Please attach vectortrack.log from that folder.)".strip()
        url = f"mailto:{self.SUPPORT_EMAIL}?subject={quote(subject)}&body={quote(body)}"
        if not QDesktopServices.openUrl(QUrl(url)):
            QMessageBox.warning(self, "Unable to open email", "No mail handler was available.")
            return
        self.accept()
