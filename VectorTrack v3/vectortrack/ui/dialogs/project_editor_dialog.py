"""Basic project and alias editor dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vectortrack.models import AliasRule, BillableProject, Client


class ProjectEditorDialog(QDialog):
    def __init__(self, repository: object, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.repository = repository
        self.setWindowTitle("Project + Alias Editor")
        self.resize(640, 420)

        layout = QHBoxLayout(self)
        self.project_list = QListWidget()
        self.project_list.currentTextChanged.connect(self._load_aliases)
        layout.addWidget(self.project_list, 1)

        editor = QVBoxLayout()
        form = QFormLayout()
        self.client_name = QLineEdit()
        self.project_code = QLineEdit()
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
        form.addRow("Project Code", self.project_code)
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
        add_alias_btn = QPushButton("Add Alias")
        add_alias_btn.clicked.connect(self._add_alias)
        self.lock_btn = QPushButton("Lock Project")
        self.lock_btn.clicked.connect(self._toggle_lock)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(create_btn)
        actions.addWidget(add_alias_btn)
        actions.addWidget(self.lock_btn)
        actions.addStretch()
        actions.addWidget(close_btn)
        editor.addLayout(actions)
        layout.addLayout(editor, 2)

        self._refresh_projects()

    def _refresh_projects(self) -> None:
        self.project_list.clear()
        projects = self.repository.list_projects(active_only=False)
        for project in projects:
            self.project_list.addItem(project.project_code)

    def _create_project(self) -> None:
        code = self.project_code.text().strip()
        name = self.project_name.text().strip()
        client_name = self.client_name.text().strip() or "Default"
        if not code or not name:
            QMessageBox.warning(self, "Missing values", "Project code and name are required.")
            return
        clients = self.repository.list_clients(active_only=False)
        client = next((c for c in clients if c.name.lower() == client_name.lower()), None)
        if client is None:
            client = self.repository.create_client(Client(name=client_name))
        self.repository.create_project(
            BillableProject(
                client_id=client.id or 0,
                project_code=code,
                name=name,
                hourly_rate=float(self.hourly_rate.value()),
            )
        )
        self._refresh_projects()
        self.project_list.setCurrentRow(max(0, self.project_list.count() - 1))

    def _load_aliases(self, project_code: str) -> None:
        self.alias_list.clear()
        if not project_code:
            self.lock_status.setText("Unlocked")
            self.lock_btn.setText("Lock Project")
            return
        project = self.repository.get_project_by_code(project_code)
        if not project or project.id is None:
            return
        self.invoice_number.setText(project.invoice_number or "")
        if project.is_locked:
            locked_at = project.locked_at or "unknown"
            self.lock_status.setText(f"Locked ({locked_at})")
            self.lock_btn.setText("Unlock Project")
            self.alias_entry.setEnabled(False)
        else:
            self.lock_status.setText("Unlocked")
            self.lock_btn.setText("Lock Project")
            self.alias_entry.setEnabled(True)
        for rule in self.repository.list_alias_rules(project_id=project.id, active_only=False):
            self.alias_list.addItem(rule.alias_pattern)

    def _toggle_lock(self) -> None:
        project_code = self.project_list.currentItem().text() if self.project_list.currentItem() else ""
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
        self._load_aliases(project_code)

    def _add_alias(self) -> None:
        project_code = self.project_list.currentItem().text() if self.project_list.currentItem() else ""
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
        self._load_aliases(project_code)

