"""Import .vtpack bundle with preview."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import pyqtSignal
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

from vectortrack.db.repository import Repository
from vectortrack.models import TimeSession
from vectortrack.services.import_export import ImportExportService


class ImportBundleDialog(QDialog):
    imported = pyqtSignal(int)

    def __init__(
        self,
        repository: Repository,
        service: ImportExportService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.service = service
        self.bundle_path: str | None = None
        self._importable_rows: list[dict[str, object]] = []

        self.setWindowTitle("Import Bundle (.vtpack)")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.path_label = QLabel("No bundle selected")
        self.path_label.setWordWrap(True)
        self.total_label = QLabel("0")
        self.dupe_label = QLabel("0")
        self.importable_label = QLabel("0")
        form.addRow("Bundle", self.path_label)
        form.addRow("Total rows", self.total_label)
        form.addRow("Duplicates", self.dupe_label)
        form.addRow("Importable", self.importable_label)
        layout.addLayout(form)

        actions = QHBoxLayout()
        select_btn = QPushButton("Choose Bundle")
        select_btn.clicked.connect(self._choose_bundle)
        self.import_btn = QPushButton("Import Rows")
        self.import_btn.clicked.connect(self._import_rows)
        self.import_btn.setEnabled(False)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        actions.addWidget(select_btn)
        actions.addWidget(self.import_btn)
        actions.addStretch()
        actions.addWidget(close_btn)
        layout.addLayout(actions)

    def _existing_rows(self) -> list[dict[str, object]]:
        return [session.to_dict() for session in self.repository.list_sessions(include_open=True, limit=20000)]

    def _choose_bundle(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose bundle",
            "",
            "VectorTrack bundle (*.vtpack *.zip);;All files (*)",
        )
        if not file_path:
            return
        self.bundle_path = file_path
        self.path_label.setText(file_path)
        try:
            importable, preview = self.service.import_rows(
                input_path=file_path,
                existing_rows=self._existing_rows(),
            )
        except Exception as exc:
            QMessageBox.warning(self, "Preview failed", str(exc))
            return
        self._importable_rows = importable
        self.total_label.setText(str(preview.total_rows))
        self.dupe_label.setText(str(preview.duplicate_rows))
        self.importable_label.setText(str(preview.importable_rows))
        self.import_btn.setEnabled(preview.importable_rows > 0)

    def _import_rows(self) -> None:
        if not self._importable_rows:
            QMessageBox.information(self, "No rows", "Nothing new to import.")
            return
        imported_count = 0
        for row in self._importable_rows:
            try:
                session = TimeSession.from_dict(row)
                saved = self.repository.upsert_open_session(session)
                if saved.id and session.end_time:
                    self.repository.close_session(saved.id, session.end_time.isoformat())
                elif saved.id and row.get("end_time"):
                    end_time = datetime.fromisoformat(str(row["end_time"]))
                    self.repository.close_session(saved.id, end_time.isoformat())
                imported_count += 1
            except Exception:
                continue
        self.imported.emit(imported_count)
        QMessageBox.information(self, "Import complete", f"Imported {imported_count} rows.")
        self.accept()
