"""Client CRUD dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vectortrack.db.repository import Repository
from vectortrack.models import Client


class ClientEditorDialog(QDialog):
    def __init__(
        self,
        repository: Repository,
        client_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.client_id = client_id
        self.setWindowTitle("Client Editor")
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.code_edit = QLineEdit()
        self.active_check = QCheckBox("Client is active")
        self.active_check.setChecked(True)
        form.addRow("Name", self.name_edit)
        form.addRow("Code", self.code_edit)
        form.addRow("", self.active_check)
        root.addLayout(form)

        actions = QHBoxLayout()
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_client)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save_client)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        actions.addWidget(self.delete_btn)
        actions.addStretch()
        actions.addWidget(self.save_btn)
        actions.addWidget(cancel_btn)
        root.addLayout(actions)

        self._load_client()

    def _load_client(self) -> None:
        if self.client_id is None:
            self.delete_btn.setEnabled(False)
            return
        client = self.repository.get_client(self.client_id)
        if client is None:
            QMessageBox.warning(self, "Client missing", "The selected client was not found.")
            self.reject()
            return
        self.name_edit.setText(client.name)
        self.code_edit.setText(client.code or "")
        self.active_check.setChecked(bool(client.is_active))

    def _save_client(self) -> None:
        name = self.name_edit.text().strip()
        code = self.code_edit.text().strip() or None
        if not name:
            QMessageBox.warning(self, "Missing name", "Client name is required.")
            return
        try:
            if self.client_id is None:
                self.repository.create_client(
                    Client(
                        name=name,
                        code=code,
                        is_active=self.active_check.isChecked(),
                    )
                )
            else:
                self.repository.update_client(
                    Client(
                        id=self.client_id,
                        name=name,
                        code=code,
                        is_active=self.active_check.isChecked(),
                    )
                )
        except Exception as exc:
            QMessageBox.warning(self, "Unable to save", str(exc))
            return
        self.accept()

    def _delete_client(self) -> None:
        if self.client_id is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete client",
            "Delete is restricted when projects reference this client.\nMark inactive instead?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        client = self.repository.get_client(self.client_id)
        if client is None:
            return
        try:
            client.is_active = False
            self.repository.update_client(client)
        except Exception as exc:
            QMessageBox.warning(self, "Unable to update", str(exc))
            return
        self.accept()
