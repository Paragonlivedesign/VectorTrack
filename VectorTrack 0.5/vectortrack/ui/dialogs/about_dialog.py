"""About dialog with Paragon branding."""

from __future__ import annotations

from urllib.parse import quote

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from vectortrack.config import COMPANY_NAME, SUPPORT_EMAIL as CFG_SUPPORT_EMAIL, VENMO_HANDLE, format_version
from vectortrack.ui.app_icon import app_icon
from vectortrack.ui.dialogs.bug_report_dialog import BugReportDialog


class AboutDialog(QDialog):
    SUPPORT_EMAIL = CFG_SUPPORT_EMAIL

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About VectorTrack")
        self.setWindowIcon(app_icon(self))
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

        support_buttons = QHBoxLayout()
        email_btn = QPushButton("Email Support")
        email_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(f"mailto:{self.SUPPORT_EMAIL}"))
        )
        feature_btn = QPushButton("Feature Request")
        feature_btn.clicked.connect(self._open_feature_request)
        bug_btn = QPushButton("Submit Bug")
        bug_btn.clicked.connect(self._open_bug_report)
        support_buttons.addWidget(email_btn)
        support_buttons.addWidget(feature_btn)
        support_buttons.addWidget(bug_btn)
        layout.addLayout(support_buttons)

        footer_buttons = QHBoxLayout()
        donate_btn = QPushButton("Donate")
        donate_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(f"https://venmo.com/{VENMO_HANDLE.lstrip('@')}"))
        )
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        footer_buttons.addWidget(donate_btn)
        footer_buttons.addStretch()
        footer_buttons.addWidget(close_btn)
        layout.addLayout(footer_buttons)

    def _open_feature_request(self) -> None:
        subject = quote("VectorTrack Feature Request")
        QDesktopServices.openUrl(QUrl(f"mailto:{self.SUPPORT_EMAIL}?subject={subject}"))

    def _open_bug_report(self) -> None:
        BugReportDialog(self).exec()

