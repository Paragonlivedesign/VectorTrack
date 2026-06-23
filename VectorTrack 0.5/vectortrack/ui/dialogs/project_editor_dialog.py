"""Basic project and alias editor dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vectortrack.models import AliasRule, BillableProject, Client
from vectortrack.ui.formatting import project_display_name, resolve_project_code


class ProjectEditorDialog(QDialog):
    def __init__(
        self,
        repository: object,
        parent: QWidget | None = None,
        initial_project_code: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self._initial_project_code = (initial_project_code or "").strip()
        self.setWindowTitle("Project + Alias Editor")
        self.resize(640, 420)

        layout = QHBoxLayout(self)
        project_column = QVBoxLayout()
        project_column.addWidget(QLabel("Projects"))
        self.project_list = QListWidget()
        self.project_list.currentItemChanged.connect(self._on_project_selected)
        project_column.addWidget(self.project_list, 1)
        layout.addLayout(project_column, 1)

        editor = QVBoxLayout()
        form = QFormLayout()
        self.client_name = QLineEdit()
        self.project_code = QLineEdit()
        self.project_code.setPlaceholderText("Optional")
        self.project_name = QLineEdit()
        self.hourly_rate = QDoubleSpinBox()
        self.hourly_rate.setRange(0, 10000)
        self.hourly_rate.setDecimals(2)
        self.hourly_rate.setValue(75.0)
        self.alias_entry = QLineEdit()
        self.alias_entry.setPlaceholderText("Alias pattern or filename")
        self.invoice_number = QLineEdit()
        self.invoice_number.setPlaceholderText("Invoice # when locking")
        self.lock_status = QLabel("Unlocked")
        form.addRow("Client", self.client_name)
        form.addRow("Project Number (optional)", self.project_code)
        form.addRow("Project Name", self.project_name)
        form.addRow("Hourly Rate", self.hourly_rate)
        form.addRow("Invoice #", self.invoice_number)
        form.addRow("Lock Status", self.lock_status)
        form.addRow("New Alias", self.alias_entry)
        editor.addLayout(form)

        self.alias_list = QListWidget()
        editor.addWidget(QLabel("Aliases"))
        editor.addWidget(self.alias_list, 1)

        actions = QHBoxLayout()
        create_btn = QPushButton("Create Project")
        create_btn.clicked.connect(self._create_project)
        self.save_btn = QPushButton("Save Project")
        self.save_btn.clicked.connect(self._save_project)
        add_alias_btn = QPushButton("Add Alias")
        add_alias_btn.clicked.connect(self._add_alias)
        self.lock_btn = QPushButton("Lock Project")
        self.lock_btn.clicked.connect(self._toggle_lock)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(create_btn)
        actions.addWidget(self.save_btn)
        actions.addWidget(add_alias_btn)
        actions.addWidget(self.lock_btn)
        actions.addStretch()
        actions.addWidget(close_btn)
        editor.addLayout(actions)
        layout.addLayout(editor, 2)

        self._refresh_projects()
        self._select_project_by_code(self._initial_project_code)

    def _refresh_projects(self) -> None:
        selected_code = self._selected_project_code()
        self.project_list.clear()
        projects = self.repository.list_projects(active_only=False)
        if not projects:
            placeholder = QListWidgetItem("(No projects yet — use Create Project)")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.project_list.addItem(placeholder)
            self._clear_form()
            return
        for project in projects:
            item_text = project_display_name(project.name, project.project_code)
            self.project_list.addItem(item_text)
            list_item = self.project_list.item(self.project_list.count() - 1)
            if list_item is not None:
                list_item.setData(Qt.ItemDataRole.UserRole, project.project_code)
        if selected_code:
            self._select_project_by_code(selected_code)

    def _select_project_by_code(self, project_code: str) -> None:
        if not project_code:
            return
        for row in range(self.project_list.count()):
            item = self.project_list.item(row)
            if item is None:
                continue
            if str(item.data(Qt.ItemDataRole.UserRole) or "") == project_code:
                self.project_list.setCurrentRow(row)
                return

    def _clear_form(self) -> None:
        self.client_name.clear()
        self.project_code.clear()
        self.project_name.clear()
        self.hourly_rate.setValue(75.0)
        self.invoice_number.clear()
        self.alias_entry.clear()
        self.alias_list.clear()
        self.lock_status.setText("Unlocked")
        self.lock_btn.setText("Lock Project")
        self.alias_entry.setEnabled(True)
        self._set_form_enabled(True)

    def _set_form_enabled(self, enabled: bool) -> None:
        self.client_name.setEnabled(enabled)
        self.project_code.setEnabled(enabled)
        self.project_name.setEnabled(enabled)
        self.hourly_rate.setEnabled(enabled)
        self.save_btn.setEnabled(enabled)

    def _selected_project_code(self) -> str:
        current = self.project_list.currentItem()
        if current is None:
            return ""
        return str(current.data(Qt.ItemDataRole.UserRole) or "")

    def _on_project_selected(self, current, _previous) -> None:
        project_code = ""
        if current is not None:
            project_code = str(current.data(Qt.ItemDataRole.UserRole) or "")
        self._load_project_details(project_code)

    def _create_project(self) -> None:
        code = self.project_code.text().strip()
        name = self.project_name.text().strip()
        client_name = self.client_name.text().strip() or "Default"
        resolved_code = resolve_project_code(name, code)
        if not resolved_code:
            QMessageBox.warning(self, "Missing values", "Project name is required.")
            return
        if self.repository.get_project_by_code(resolved_code) is not None:
            QMessageBox.warning(self, "Duplicate project", f"A project with key '{resolved_code}' already exists.")
            return
        clients = self.repository.list_clients(active_only=False)
        client = next((c for c in clients if c.name.lower() == client_name.lower()), None)
        if client is None:
            client = self.repository.create_client(Client(name=client_name))
        self.repository.create_project(
            BillableProject(
                client_id=client.id or 0,
                project_code=resolved_code,
                name=name,
                hourly_rate=float(self.hourly_rate.value()),
            )
        )
        self._refresh_projects()
        self._select_project_by_code(resolved_code)

    def _save_project(self) -> None:
        project_code = self._selected_project_code()
        if not project_code:
            QMessageBox.information(self, "No project", "Select a project first.")
            return
        project = self.repository.get_project_by_code(project_code)
        if not project or project.id is None:
            QMessageBox.warning(self, "Project missing", "Selected project was not found.")
            return
        if project.is_locked:
            QMessageBox.warning(self, "Project locked", "Unlock the project before editing.")
            return

        name = self.project_name.text().strip()
        code = self.project_code.text().strip()
        client_name = self.client_name.text().strip() or "Default"
        resolved_code = resolve_project_code(name, code)
        if not resolved_code:
            QMessageBox.warning(self, "Missing values", "Project name is required.")
            return
        if resolved_code != project_code:
            existing = self.repository.get_project_by_code(resolved_code)
            if existing is not None:
                QMessageBox.warning(
                    self,
                    "Duplicate project",
                    f"A project with key '{resolved_code}' already exists.",
                )
                return

        clients = self.repository.list_clients(active_only=False)
        client = next((c for c in clients if c.name.lower() == client_name.lower()), None)
        if client is None:
            client = self.repository.create_client(Client(name=client_name))

        try:
            self.repository.update_project(
                BillableProject(
                    id=project.id,
                    client_id=client.id or project.client_id,
                    project_code=resolved_code,
                    name=name,
                    hourly_rate=float(self.hourly_rate.value()),
                    is_active=project.is_active,
                    is_locked=project.is_locked,
                    locked_at=project.locked_at,
                    invoice_number=project.invoice_number,
                )
            )
        except PermissionError as exc:
            QMessageBox.warning(self, "Project locked", str(exc))
            return

        self._refresh_projects()
        self._select_project_by_code(resolved_code)

    def _load_project_details(self, project_code: str) -> None:
        self.alias_list.clear()
        if not project_code:
            self._clear_form()
            return
        project = self.repository.get_project_by_code(project_code)
        if not project or project.id is None:
            self._clear_form()
            return

        client = self.repository.get_client(project.client_id)
        self.client_name.setText(client.name if client else "")
        self.project_name.setText(project.name)
        stored_code = project.project_code.strip()
        display_code = "" if stored_code == project.name.strip() else stored_code
        self.project_code.setText(display_code)
        self.hourly_rate.setValue(float(project.hourly_rate))
        self.invoice_number.setText(project.invoice_number or "")

        if project.is_locked:
            locked_at = project.locked_at or "unknown"
            self.lock_status.setText(f"Locked ({locked_at})")
            self.lock_btn.setText("Unlock Project")
            self.alias_entry.setEnabled(False)
            self._set_form_enabled(False)
        else:
            self.lock_status.setText("Unlocked")
            self.lock_btn.setText("Lock Project")
            self.alias_entry.setEnabled(True)
            self._set_form_enabled(True)

        for rule in self.repository.list_alias_rules(project_id=project.id, active_only=False):
            self.alias_list.addItem(rule.alias_pattern)

    def _toggle_lock(self) -> None:
        project_code = self._selected_project_code()
        if not project_code:
            QMessageBox.information(self, "No project", "Select a project first.")
            return
        project = self.repository.get_project_by_code(project_code)
        if not project:
            return
        if project.is_locked:
            self.repository.set_project_lock(project_code, locked=False)
        else:
            invoice = self.invoice_number.text().strip()
            if not invoice:
                QMessageBox.warning(self, "Invoice required", "Enter an invoice number before locking.")
                return
            self.repository.set_project_lock(project_code, locked=True, invoice_number=invoice)
        self._load_project_details(project_code)

    def _add_alias(self) -> None:
        project_code = self._selected_project_code()
        alias = self.alias_entry.text().strip()
        if not project_code or not alias:
            QMessageBox.warning(self, "Missing values", "Choose a project and enter alias text.")
            return
        project = self.repository.get_project_by_code(project_code)
        if not project or project.id is None:
            QMessageBox.warning(self, "Project missing", "Selected project was not found.")
            return
        if project.is_locked:
            QMessageBox.warning(self, "Project locked", "Unlock the project before editing aliases.")
            return
        self.repository.upsert_alias_rule(AliasRule(project_id=project.id, alias_pattern=alias))
        self.alias_entry.clear()
        self._load_project_details(project_code)

