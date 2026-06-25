"""Manage Vectorworks log sources and open linked log files."""

from __future__ import annotations

import os
import subprocess
import sys

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFileDialog,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vectortrack.log_parser import VW_LOG_TIME_PREFERENCE_HELP
from vectortrack.db.repository import Repository


class LogLibraryDialog(QDialog):
    def __init__(
        self,
        repository: Repository,
        linked_log_paths: list[str] | None = None,
        linked_log_description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.linked_log_paths = list(linked_log_paths or [])
        self.linked_log_description = linked_log_description.strip()
        self.setWindowTitle("Log Library")
        self.resize(720, 520)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "VectorTrack reads Vectorworks Log.txt for imported session history. "
                "Logs below are linked automatically from your Vectorworks install. "
                "Add extra log files only if you use a custom location or another machine's copy.\n\n"
                f"{VW_LOG_TIME_PREFERENCE_HELP}"
            )
        )
        if self.linked_log_description:
            desc = QLabel(f"Active link: {self.linked_log_description}")
            desc.setWordWrap(True)
            layout.addWidget(desc)

        linked_group = QGroupBox("Linked Vectorworks logs (automatic)")
        linked_layout = QVBoxLayout(linked_group)
        self.linked_list = QListWidget(linked_group)
        linked_layout.addWidget(self.linked_list, 1)
        linked_actions = QHBoxLayout()
        open_log_btn = QPushButton("Open Log File")
        open_log_btn.clicked.connect(self._open_selected_linked_log)
        open_folder_btn = QPushButton("Open Log Folder")
        open_folder_btn.clicked.connect(self._open_selected_linked_folder)
        linked_actions.addWidget(open_log_btn)
        linked_actions.addWidget(open_folder_btn)
        linked_actions.addStretch()
        linked_layout.addLayout(linked_actions)
        layout.addWidget(linked_group, 1)

        extra_group = QGroupBox("Additional log sources (optional)")
        extra_layout = QVBoxLayout(extra_group)
        self.source_list = QListWidget(extra_group)
        extra_layout.addWidget(self.source_list, 1)
        extra_actions = QHBoxLayout()
        add_btn = QPushButton("Add Log File…")
        add_btn.clicked.connect(self._add_source)
        remove_btn = QPushButton("Remove Source")
        remove_btn.clicked.connect(self._remove_source)
        open_extra_btn = QPushButton("Open Selected")
        open_extra_btn.clicked.connect(self._open_selected_extra_log)
        extra_actions.addWidget(add_btn)
        extra_actions.addWidget(remove_btn)
        extra_actions.addWidget(open_extra_btn)
        extra_actions.addStretch()
        extra_layout.addLayout(extra_actions)
        layout.addWidget(extra_group, 1)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

        self._refresh_linked()
        self._refresh_sources()

    def _refresh_linked(self) -> None:
        self.linked_list.clear()
        if not self.linked_log_paths:
            item = QListWidgetItem(
                "(No Vectorworks logs found — link Vectorworks via File menu, or add a log file below)"
            )
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.linked_list.addItem(item)
            return
        for path in self.linked_log_paths:
            norm = os.path.normpath(path)
            exists = os.path.isfile(norm)
            label = norm if exists else f"{norm}  (missing)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, norm)
            if not exists:
                item.setForeground(self.palette().color(self.foregroundRole()))
            self.linked_list.addItem(item)

    def _refresh_sources(self) -> None:
        self.source_list.clear()
        for source in self.repository.list_log_sources():
            line = str(source.get("source", ""))
            description = str(source.get("description") or "")
            if description:
                line = f"{line}  -  {description}"
            item = QListWidgetItem(line)
            item.setData(Qt.ItemDataRole.UserRole, str(source.get("source", "")).strip())
            self.source_list.addItem(item)

    def _selected_linked_path(self) -> str:
        item = self.linked_list.currentItem()
        if item is None:
            return ""
        return str(item.data(Qt.ItemDataRole.UserRole) or "").strip()

    def _selected_extra_path(self) -> str:
        item = self.source_list.currentItem()
        if item is None:
            return ""
        text = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
        if text:
            return text
        return item.text().split("  -  ", 1)[0].strip()

    def _open_path(self, path: str, *, kind: str) -> None:
        if not path:
            QMessageBox.information(self, f"Select {kind}", f"Select a {kind.lower()} first.")
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "Not found", f"Path does not exist:\n{path}")
            return
        if sys.platform.startswith("win"):
            try:
                if os.path.isfile(path):
                    subprocess.run(["explorer", "/select,", os.path.normpath(path)], check=False)
                else:
                    os.startfile(os.path.normpath(path))  # noqa: S606
                return
            except OSError:
                pass
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _open_selected_linked_log(self) -> None:
        self._open_path(self._selected_linked_path(), kind="log file")

    def _open_selected_linked_folder(self) -> None:
        path = self._selected_linked_path()
        if not path:
            QMessageBox.information(self, "Select log", "Select a linked log first.")
            return
        self._open_path(os.path.dirname(path), kind="folder")

    def _open_selected_extra_log(self) -> None:
        self._open_path(self._selected_extra_path(), kind="log file")

    def _add_source(self) -> None:
        start_dir = ""
        if self.linked_log_paths:
            start_dir = os.path.dirname(self.linked_log_paths[0])
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Vectorworks log",
            start_dir,
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
        source = self._selected_extra_path()
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
