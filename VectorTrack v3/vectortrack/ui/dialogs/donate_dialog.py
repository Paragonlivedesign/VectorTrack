"""Simple donate dialog with copy-able Venmo handle."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from vectortrack.config import DONATE_MESSAGE, VENMO_HANDLE as CFG_VENMO_HANDLE


class DonateDialog(QDialog):
    VENMO_HANDLE = CFG_VENMO_HANDLE

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Support VectorTrack")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(DONATE_MESSAGE))
        handle = QLabel(f"Venmo: {self.VENMO_HANDLE}")
        handle.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(handle)
        buttons = QHBoxLayout()
        copy_btn = QPushButton("Copy Venmo")
        copy_btn.clicked.connect(self._copy_venmo)
        open_btn = QPushButton("Open Venmo")
        open_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(f"https://venmo.com/{self.VENMO_HANDLE.lstrip('@')}"))
        )
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(copy_btn)
        buttons.addWidget(open_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def _copy_venmo(self) -> None:
        QGuiApplication.clipboard().setText(self.VENMO_HANDLE)

