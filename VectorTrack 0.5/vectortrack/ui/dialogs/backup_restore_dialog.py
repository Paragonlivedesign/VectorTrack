"""Backup/restore dialog."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vectortrack import config
from vectortrack.services.backup_service import BackupService


class BackupRestoreDialog(QDialog):
    def __init__(self, service: BackupService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Backup + Restore")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.last_backup_label = QLabel("Not created yet")
        self.last_restore_label = QLabel("No restore run")
        form.addRow("Last backup", self.last_backup_label)
        form.addRow("Last restore", self.last_restore_label)
        layout.addLayout(form)

        actions = QHBoxLayout()
        backup_btn = QPushButton("Backup Now")
        backup_btn.clicked.connect(self._backup_now)
        restore_btn = QPushButton("Restore Archive")
        restore_btn.clicked.connect(self._restore_archive)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(backup_btn)
        actions.addWidget(restore_btn)
        actions.addStretch()
        actions.addWidget(close_btn)
        layout.addLayout(actions)

    def _backup_now(self) -> None:
        data_dir = config.resolve_data_dir()
        targets = [
            str(data_dir / config.DEFAULT_DB_FILENAME),
            "reports",
            str(config.logs_dir()),
        ]
        try:
            backup_path = self.service.create_backup(targets, label="vectortrack")
        except Exception as exc:
            QMessageBox.warning(self, "Backup failed", str(exc))
            return
        self.last_backup_label.setText(backup_path)
        QMessageBox.information(self, "Backup complete", f"Created:\n{backup_path}")

    def _restore_archive(self) -> None:
        backup_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose backup archive",
            str(self.service.backup_dir),
            "Zip archive (*.zip);;All files (*)",
        )
        if not backup_path:
            return
        destination = str(config.resolve_data_dir())
        answer = QMessageBox.question(
            self,
            "Confirm restore",
            "Restore files into your VectorTrack data directory?\nExisting files may be overwritten.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            restored = self.service.restore_backup(backup_path, destination, overwrite=True)
        except Exception as exc:
            QMessageBox.warning(self, "Restore failed", str(exc))
            return
        self.last_restore_label.setText(f"{len(restored)} files")
        QMessageBox.information(
            self,
            "Restore complete",
            f"Restored {len(restored)} files into:\n{destination}",
        )
