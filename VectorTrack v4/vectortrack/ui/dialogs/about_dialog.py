"""About dialog with Paragon branding."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from vectortrack.config import COMPANY_NAME, SUPPORT_EMAIL as CFG_SUPPORT_EMAIL, VENMO_HANDLE, format_version


class AboutDialog(QDialog):
    SUPPORT_EMAIL = CFG_SUPPORT_EMAIL

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About VectorTrack")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        title = QLabel(format_version(include_product_name=True))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        branding = QLabel(
            f"Built by {COMPANY_NAME}.\n"
            "Track Vectorworks time with live session, history, and billing context."
        )
        branding.setAlignment(Qt.AlignmentFlag.AlignCenter)
        branding.setWordWrap(True)
        layout.addWidget(branding)

        contact = QLabel(f"Support: {self.SUPPORT_EMAIL}\nWebsite: paragonlivedesign.com")
        contact.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(contact)

        venmo = QLabel(f"Venmo: {VENMO_HANDLE}")
        venmo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        venmo.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(venmo)

        buttons = QHBoxLayout()
        donate_btn = QPushButton("Donate")
        donate_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(f"https://venmo.com/{VENMO_HANDLE.lstrip('@')}"))
        )
        email_btn = QPushButton("Email Support")
        email_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(f"mailto:{self.SUPPORT_EMAIL}"))
        )
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(donate_btn)
        buttons.addWidget(email_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

