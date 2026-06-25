"""Dialog for checking GitHub Releases for VectorTrack updates."""

from __future__ import annotations

from PyQt6.QtCore import QObject, Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from vectortrack.config import APP_BETA, format_version
from vectortrack.services.update_service import UpdateCheckResult, check_for_updates
from vectortrack.ui.app_icon import app_icon


class _UpdateCheckWorker(QObject):
    finished = pyqtSignal(object)

    def run(self) -> None:
        self.finished.emit(check_for_updates())


class UpdateCheckDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Check for Updates")
        self.setWindowIcon(app_icon(self))
        self.setMinimumWidth(480)
        self._thread: QThread | None = None
        self._worker: _UpdateCheckWorker | None = None

        layout = QVBoxLayout(self)
        self.status_label = QLabel("Checking for updates...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.notes = QTextEdit()
        self.notes.setReadOnly(True)
        self.notes.hide()
        self.notes.setMaximumHeight(180)
        layout.addWidget(self.notes)

        buttons = QHBoxLayout()
        self.download_btn = QPushButton("Open Download Page")
        self.download_btn.hide()
        self.download_btn.clicked.connect(self._open_download_page)
        self.retry_btn = QPushButton("Try Again")
        self.retry_btn.hide()
        self.retry_btn.clicked.connect(self._start_check)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(self.download_btn)
        buttons.addWidget(self.retry_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self._release_url = ""
        self._start_check()

    def _start_check(self) -> None:
        self._cleanup_thread()
        self.status_label.setText("Checking for updates...")
        self.notes.hide()
        self.notes.clear()
        self.download_btn.hide()
        self.retry_btn.hide()
        self._release_url = ""

        self._thread = QThread(self)
        self._worker = _UpdateCheckWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_check_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _cleanup_thread(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        self._thread = None
        self._worker = None

    def _on_check_finished(self, result: object) -> None:
        if not isinstance(result, UpdateCheckResult):
            self._show_error("Update check failed unexpectedly.")
            return
        if result.error:
            self._show_error(result.error)
            return
        if result.latest is None:
            self._show_error("No release information was returned.")
            return

        current_label = format_version(include_product_name=False)
        latest_label = result.latest.version_label
        if APP_BETA and not latest_label.endswith("beta"):
            latest_label = f"{latest_label} beta"

        if result.update_available:
            self.status_label.setText(
                f"A newer version is available.\n\n"
                f"You have {current_label}.\n"
                f"Latest release: {latest_label}."
            )
            if result.latest.notes:
                self.notes.setPlainText(result.latest.notes)
                self.notes.show()
            self._release_url = result.latest.download_url or result.latest.release_url
            self.download_btn.show()
            return

        self.status_label.setText(
            f"You are up to date.\n\nVectorTrack {current_label} is the latest release."
        )

    def _show_error(self, message: str) -> None:
        self.status_label.setText(f"Could not check for updates.\n\n{message}")
        self.retry_btn.show()

    def _open_download_page(self) -> None:
        if self._release_url:
            QDesktopServices.openUrl(QUrl(self._release_url))

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._cleanup_thread()
        super().closeEvent(event)
