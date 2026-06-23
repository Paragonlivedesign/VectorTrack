"""Manage additional log sources."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QFileDialog,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vectortrack.db.repository import Repository


class LogLibraryDialog(QDialog):
    def __init__(self, repository: Repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.repository = repository
        self.setWindowTitle("Log Library")
        self.resize(640, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Registered log sources"))
        self.source_list = QListWidget(self)
        layout.addWidget(self.source_list, 1)

        actions = QHBoxLayout()
        add_btn = QPushButton("Add Source")
        add_btn.clicked.connect(self._add_source)
        remove_btn = QPushButton("Remove Source")
        remove_btn.clicked.connect(self._remove_source)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(add_btn)
        actions.addWidget(remove_btn)
        actions.addStretch()
        actions.addWidget(close_btn)
        layout.addLayout(actions)

        self._refresh_sources()

    def _refresh_sources(self) -> None:
        self.source_list.clear()
        for source in self.repository.list_log_sources():
            line = str(source.get("source", ""))
            description = str(source.get("description") or "")
            if description:
                line = f"{line}  -  {description}"
            self.source_list.addItem(line)

    def _add_source(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Vectorworks log",
            "",
            "Log files (*.log *.txt);;All files (*)",
        )
        if not file_path:
            return
        try:
            self.repository.register_log_source(file_path, "User-added")
        except Exception as exc:
            QMessageBox.warning(self, "Unable to add source", str(exc))
            return
        self._refresh_sources()

    def _remove_source(self) -> None:
        item = self.source_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Select source", "Select a source to remove.")
            return
        source = item.text().split("  -  ", 1)[0].strip()
        if not hasattr(self.repository, "remove_log_source"):
            QMessageBox.warning(
                self,
                "Repository action unavailable",
                "This build cannot remove log sources yet.",
            )
            return
        try:
            self.repository.remove_log_source(source)
        except Exception as exc:
            QMessageBox.warning(self, "Unable to remove source", str(exc))
            return
        self._refresh_sources()
