"""Project editor with details, assigned files, and alias management."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vectortrack.budget import (
    BudgetType,
    ProjectBudget,
    load_project_budget,
    migrate_project_budget,
    save_project_budget,
)
from vectortrack.models import AliasRule, BillableProject, Client
from vectortrack.ui.formatting import project_display_name, resolve_project_code


class ProjectEditorDialog(QDialog):
    def __init__(
        self,
        repository: object,
        parent: QWidget | None = None,
        initial_project_code: str | None = None,
        *,
        file_assignments: dict[str, str] | None = None,
        on_unassign_file: Callable[[str], None] | None = None,
        on_catalog_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self._initial_project_code = (initial_project_code or "").strip()
        self._file_assignments = file_assignments if file_assignments is not None else {}
        self._on_unassign_file = on_unassign_file
        self._on_catalog_changed = on_catalog_changed
        self._projects: list[BillableProject] = []
        self.setWindowTitle("Project Editor")
        self.resize(980, 680)

        root = QHBoxLayout(self)

        sidebar = QVBoxLayout()
        sidebar.addWidget(QLabel("Projects"))
        self.project_filter = QLineEdit()
        self.project_filter.setPlaceholderText("Search projects...")
        self.project_filter.textChanged.connect(self._apply_project_filter)
        sidebar.addWidget(self.project_filter)
        self.project_list = QListWidget()
        self.project_list.currentItemChanged.connect(self._on_project_selected)
        sidebar.addWidget(self.project_list, 1)
        root.addLayout(sidebar, 1)

        right = QVBoxLayout()

        details_group = QGroupBox("Project Details")
        details_layout = QGridLayout(details_group)
        self.client_name = QLineEdit()
        self.project_code = QLineEdit()
        self.project_code.setPlaceholderText("Optional")
        self.project_name = QLineEdit()
        self.hourly_rate = QDoubleSpinBox()
        self.hourly_rate.setRange(0, 10000)
        self.hourly_rate.setDecimals(2)
        self.hourly_rate.setValue(75.0)
        self.budget_type = QComboBox()
        self.budget_type.addItems(["No budget", "Hours", "Money"])
        self.budget_type.setToolTip("Track progress against hours or a dollar amount — not both.")
        self.budget_type.currentIndexChanged.connect(self._on_budget_type_changed)
        self.budget_amount = QDoubleSpinBox()
        self.budget_amount.setRange(0, 10000000)
        self.budget_amount.setDecimals(2)
        self.budget_amount.setToolTip("Drives the progress bar on the Projects tab.")
        self.invoice_number = QLineEdit()
        self.invoice_number.setPlaceholderText("Invoice # when locking")
        self.lock_status = QLabel("Unlocked")
        self.lock_status.setObjectName("muted")

        details_layout.addWidget(QLabel("Client"), 0, 0)
        details_layout.addWidget(self.client_name, 0, 1)
        details_layout.addWidget(QLabel("Project Number"), 0, 2)
        details_layout.addWidget(self.project_code, 0, 3)
        details_layout.addWidget(QLabel("Project Name"), 1, 0)
        details_layout.addWidget(self.project_name, 1, 1, 1, 3)
        details_layout.addWidget(QLabel("Hourly Rate"), 2, 0)
        details_layout.addWidget(self.hourly_rate, 2, 1)
        details_layout.addWidget(QLabel("Budget"), 2, 2)
        budget_row = QHBoxLayout()
        budget_row.addWidget(self.budget_type)
        budget_row.addWidget(self.budget_amount, 1)
        budget_widget = QWidget()
        budget_widget.setLayout(budget_row)
        details_layout.addWidget(budget_widget, 2, 3)
        details_layout.addWidget(QLabel("Invoice #"), 3, 0)
        details_layout.addWidget(self.invoice_number, 3, 1)
        details_layout.addWidget(QLabel("Lock Status"), 3, 2)
        details_layout.addWidget(self.lock_status, 3, 3)
        right.addWidget(details_group)

        summary_row = QHBoxLayout()
        self.summary_sessions = QLabel("0 sessions")
        self.summary_sessions.setObjectName("muted")
        self.summary_tracked = QLabel("0.00h tracked")
        self.summary_tracked.setObjectName("muted")
        self.summary_billable = QLabel("$0.00 billable")
        self.summary_billable.setObjectName("muted")
        self.summary_aliases = QLabel("0 aliases")
        self.summary_aliases.setObjectName("muted")
        summary_row.addWidget(self.summary_sessions)
        summary_row.addWidget(self.summary_tracked)
        summary_row.addWidget(self.summary_billable)
        summary_row.addWidget(self.summary_aliases)
        summary_row.addStretch()
        right.addLayout(summary_row)

        self.budget_progress = QProgressBar()
        self.budget_progress.setRange(0, 100)
        self.budget_progress.setFormat("Budget: %p%")
        self.budget_progress.hide()
        right.addWidget(self.budget_progress)

        splitter = QSplitter(Qt.Orientation.Vertical)

        files_group = QGroupBox("Assigned Files")
        files_layout = QVBoxLayout(files_group)
        self.files_table = QTableWidget(0, 4)
        self.files_table.setHorizontalHeaderLabels(["File", "Status", "Tracked", ""])
        self.files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.files_table.verticalHeader().setVisible(False)
        header = self.files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        files_layout.addWidget(self.files_table)
        self.files_hint = QLabel("Select a project to view assigned files.")
        self.files_hint.setObjectName("muted")
        self.files_hint.setWordWrap(True)
        files_layout.addWidget(self.files_hint)
        splitter.addWidget(files_group)

        aliases_group = QGroupBox("Filename Aliases")
        aliases_layout = QVBoxLayout(aliases_group)
        alias_row = QHBoxLayout()
        self.alias_entry = QLineEdit()
        self.alias_entry.setPlaceholderText("Alias pattern or filename")
        add_alias_btn = QPushButton("Add Alias")
        add_alias_btn.clicked.connect(self._add_alias)
        alias_row.addWidget(self.alias_entry, 1)
        alias_row.addWidget(add_alias_btn)
        aliases_layout.addLayout(alias_row)
        self.alias_list = QListWidget()
        aliases_layout.addWidget(self.alias_list, 1)
        splitter.addWidget(aliases_group)
        splitter.setSizes([320, 180])
        right.addWidget(splitter, 1)

        actions = QHBoxLayout()
        create_btn = QPushButton("Create Project")
        create_btn.clicked.connect(self._create_project)
        self.save_btn = QPushButton("Save Project")
        self.save_btn.clicked.connect(self._save_project)
        self.lock_btn = QPushButton("Lock Project")
        self.lock_btn.clicked.connect(self._toggle_lock)
        delete_btn = QPushButton("Delete Project")
        delete_btn.clicked.connect(self._delete_project)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(create_btn)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.lock_btn)
        actions.addWidget(delete_btn)
        actions.addStretch()
        actions.addWidget(close_btn)
        right.addLayout(actions)
        root.addLayout(right, 3)

        self._refresh_projects()
        self._select_project_by_code(self._initial_project_code)

    def _refresh_projects(self) -> None:
        selected_code = self._selected_project_code()
        self._projects = self.repository.list_projects(active_only=False)
        self._apply_project_filter(self.project_filter.text())

        if not self._projects:
            self.project_list.clear()
            placeholder = QListWidgetItem("(No projects yet — use Create Project)")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.project_list.addItem(placeholder)
            self._clear_form()
            return
        if selected_code:
            self._select_project_by_code(selected_code)

    def _apply_project_filter(self, text: str) -> None:
        needle = text.strip().lower()
        selected_code = self._selected_project_code()
        self.project_list.blockSignals(True)
        self.project_list.clear()
        visible_codes: list[str] = []
        for project in self._projects:
            label = project_display_name(project.name, project.project_code)
            if project.is_locked:
                label += " [LOCKED]"
            haystack = f"{label} {project.project_code} {project.name}".lower()
            if needle and needle not in haystack:
                continue
            self.project_list.addItem(label)
            list_item = self.project_list.item(self.project_list.count() - 1)
            if list_item is not None:
                list_item.setData(Qt.ItemDataRole.UserRole, project.project_code)
                visible_codes.append(project.project_code)
        self.project_list.blockSignals(False)
        if selected_code and selected_code in visible_codes:
            self._select_project_by_code(selected_code)
        elif self.project_list.count() > 0:
            self.project_list.setCurrentRow(0)
        elif not needle:
            self._clear_form()

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
        self.budget_type.setCurrentIndex(0)
        self.budget_amount.setValue(0.0)
        self._apply_budget_type_ui(BudgetType.NONE)
        self.invoice_number.clear()
        self.alias_entry.clear()
        self.alias_list.clear()
        self.files_table.setRowCount(0)
        self.lock_status.setText("Unlocked")
        self.lock_btn.setText("Lock Project")
        self.alias_entry.setEnabled(True)
        self.summary_sessions.setText("0 sessions")
        self.summary_tracked.setText("0.00h tracked")
        self.summary_billable.setText("$0.00 billable")
        self.summary_aliases.setText("0 aliases")
        self.budget_progress.hide()
        self.files_hint.setText("Select a project to view assigned files.")
        self._set_form_enabled(True)

    def _set_form_enabled(self, enabled: bool) -> None:
        self.client_name.setEnabled(enabled)
        self.project_code.setEnabled(enabled)
        self.project_name.setEnabled(enabled)
        self.hourly_rate.setEnabled(enabled)
        self.save_btn.setEnabled(enabled)

    def _apply_budget_type_ui(self, budget_type: BudgetType) -> None:
        enabled = budget_type != BudgetType.NONE
        self.budget_amount.setEnabled(enabled)
        if budget_type == BudgetType.MONEY:
            self.budget_amount.setPrefix("$")
            self.budget_amount.setSuffix("")
        elif budget_type == BudgetType.HOURS:
            self.budget_amount.setPrefix("")
            self.budget_amount.setSuffix(" h")
        else:
            self.budget_amount.setPrefix("")
            self.budget_amount.setSuffix("")
            self.budget_amount.setValue(0.0)

    def _on_budget_type_changed(self, index: int) -> None:
        budget_type = {
            0: BudgetType.NONE,
            1: BudgetType.HOURS,
            2: BudgetType.MONEY,
        }.get(index, BudgetType.NONE)
        self._apply_budget_type_ui(budget_type)

    def _budget_from_form(self) -> ProjectBudget:
        index = self.budget_type.currentIndex()
        amount = float(self.budget_amount.value())
        if index == 1 and amount > 0:
            return ProjectBudget(BudgetType.HOURS, amount)
        if index == 2 and amount > 0:
            return ProjectBudget(BudgetType.MONEY, amount)
        return ProjectBudget(BudgetType.NONE, 0.0)

    def _load_budget(self, project_code: str) -> ProjectBudget:
        budget = load_project_budget(self.repository, project_code)
        if budget.budget_type == BudgetType.MONEY:
            self.budget_type.setCurrentIndex(2)
        elif budget.budget_type == BudgetType.HOURS:
            self.budget_type.setCurrentIndex(1)
        else:
            self.budget_type.setCurrentIndex(0)
        self._apply_budget_type_ui(budget.budget_type)
        self.budget_amount.setValue(budget.amount if budget.has_budget else 0.0)
        return budget

    def _save_budget(self, project_code: str) -> None:
        save_project_budget(self.repository, project_code, self._budget_from_form())

    def _session_stats_by_file(self, project_code: str) -> dict[str, dict[str, Any]]:
        stats: dict[str, dict[str, Any]] = {}
        for session in self.repository.list_sessions(project_id=project_code, include_open=True, limit=15000):
            path = (session.file_path or "").strip()
            if not path:
                continue
            agg = stats.setdefault(path, {"hours": 0.0, "has_open": False})
            agg["hours"] += session.active_duration.total_seconds() / 3600.0
            if session.end_time is None:
                agg["has_open"] = True
        return stats

    def _assigned_file_rows(self, project_code: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        stats = self._session_stats_by_file(project_code)

        for path, code in self._file_assignments.items():
            if str(code).strip() != project_code or not path:
                continue
            seen.add(path)
            status = "Assigned"
            if stats.get(path, {}).get("has_open"):
                status = "Assigned · open"
            rows.append(
                {
                    "file_path": path,
                    "status": status,
                    "can_unassign": True,
                    "hours": float(stats.get(path, {}).get("hours", 0.0)),
                }
            )

        for path, agg in stats.items():
            if path in seen:
                continue
            seen.add(path)
            rows.append(
                {
                    "file_path": path,
                    "status": "Open session" if agg["has_open"] else "Session history",
                    "can_unassign": False,
                    "hours": float(agg["hours"]),
                }
            )

        rows.sort(key=lambda item: os.path.basename(str(item["file_path"])).lower())
        return rows

    def _refresh_assigned_files(self, project_code: str) -> None:
        self.files_table.setRowCount(0)
        if not project_code:
            self.files_hint.setText("Select a project to view assigned files.")
            return

        rows = self._assigned_file_rows(project_code)
        if not rows:
            self.files_hint.setText("No files are assigned to this project yet.")
            return

        override_count = sum(1 for row in rows if row["can_unassign"])
        self.files_hint.setText(
            f"{len(rows)} file(s) linked to this project "
            f"({override_count} active assignment{'s' if override_count != 1 else ''})."
        )

        for data in rows:
            row = self.files_table.rowCount()
            self.files_table.insertRow(row)
            file_path = str(data["file_path"])
            name_item = QTableWidgetItem(os.path.basename(file_path))
            name_item.setToolTip(file_path)
            name_item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.files_table.setItem(row, 0, name_item)
            self.files_table.setItem(row, 1, QTableWidgetItem(str(data["status"])))
            self.files_table.setItem(row, 2, QTableWidgetItem(f'{float(data["hours"]):.2f}h'))

            if data["can_unassign"]:
                unassign_btn = QPushButton("Unassign")
                unassign_btn.clicked.connect(
                    lambda _checked=False, fp=file_path: self._unassign_file(fp)
                )
                self.files_table.setCellWidget(row, 3, unassign_btn)
            else:
                self.files_table.setItem(row, 3, QTableWidgetItem(""))

    def _unassign_file(self, file_path: str) -> None:
        if not file_path:
            return
        answer = QMessageBox.question(
            self,
            "Unassign file",
            f"Remove project assignment for\n{os.path.basename(file_path)}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self._on_unassign_file is not None:
            self._on_unassign_file(file_path)
        self._file_assignments.pop(file_path, None)
        project_code = self._selected_project_code()
        if project_code:
            self._refresh_assigned_files(project_code)

    def _refresh_summary(self, project_code: str, *, alias_count: int, budget: ProjectBudget) -> None:
        sessions = self.repository.list_sessions(project_id=project_code, include_open=True, limit=15000)
        tracked = sum(session.active_duration.total_seconds() / 3600.0 for session in sessions)
        billable = sum(float(session.billable_amount) for session in sessions)
        self.summary_sessions.setText(f"{len(sessions)} session{'s' if len(sessions) != 1 else ''}")
        self.summary_tracked.setText(f"{tracked:.2f}h tracked")
        self.summary_billable.setText(f"${billable:.2f} billable")
        self.summary_aliases.setText(f"{alias_count} alias{'es' if alias_count != 1 else ''}")

        if not budget.has_budget:
            self.budget_progress.hide()
            return
        if budget.budget_type == BudgetType.MONEY:
            used, limit = billable, budget.amount
            detail = f"${used:.2f} / ${limit:.2f}"
        else:
            used, limit = tracked, budget.amount
            detail = f"{used:.1f} / {limit:.1f} h"
        progress_pct = max(0, min(100, int((used / limit) * 100)))
        self.budget_progress.setValue(progress_pct)
        self.budget_progress.setFormat(f"Budget: {progress_pct}% ({detail})")
        if used > limit:
            self.budget_progress.setStyleSheet("QProgressBar::chunk { background-color: #c44242; }")
        elif used >= limit * 0.8:
            self.budget_progress.setStyleSheet("QProgressBar::chunk { background-color: #d4a72c; }")
        else:
            self.budget_progress.setStyleSheet("QProgressBar::chunk { background-color: #2a9d5a; }")
        self.budget_progress.show()

    def _notify_catalog_changed(self) -> None:
        if self._on_catalog_changed is not None:
            self._on_catalog_changed()

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
        self._save_budget(resolved_code)
        self._notify_catalog_changed()
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
            self._save_budget(project_code)
            self._notify_catalog_changed()
            QMessageBox.information(
                self,
                "Budget saved",
                "Budget updated. Other project fields are locked for billing.",
            )
            self._load_project_details(project_code)
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

        if resolved_code != project_code:
            migrate_project_budget(self.repository, project_code, resolved_code)
            for path, assigned_code in list(self._file_assignments.items()):
                if assigned_code == project_code:
                    self._file_assignments[path] = resolved_code
        self._save_budget(resolved_code)
        self._notify_catalog_changed()

        self._refresh_projects()
        self._select_project_by_code(resolved_code)

    def _load_project_details(self, project_code: str) -> None:
        self.alias_list.clear()
        self.files_table.setRowCount(0)
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
        budget = self._load_budget(project_code)
        self.invoice_number.setText(project.invoice_number or "")

        alias_rules = self.repository.list_alias_rules(project_id=project.id, active_only=False)
        for rule in alias_rules:
            self.alias_list.addItem(rule.alias_pattern)

        if project.is_locked:
            locked_at = project.locked_at or "unknown"
            self.lock_status.setText(f"Locked ({locked_at})")
            self.lock_btn.setText("Unlock Project")
            self.alias_entry.setEnabled(False)
            self._set_form_enabled(False)
            self.save_btn.setEnabled(True)
            self.budget_type.setEnabled(True)
            self.budget_amount.setEnabled(budget.budget_type != BudgetType.NONE)
        else:
            self.lock_status.setText("Unlocked")
            self.lock_btn.setText("Lock Project")
            self.alias_entry.setEnabled(True)
            self._set_form_enabled(True)
            self.budget_type.setEnabled(True)
            self.budget_amount.setEnabled(budget.budget_type != BudgetType.NONE)

        self._refresh_summary(project_code, alias_count=len(alias_rules), budget=budget)
        self._refresh_assigned_files(project_code)

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
        self._notify_catalog_changed()
        self._refresh_projects()
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
        self._notify_catalog_changed()
        self._load_project_details(project_code)

    def _delete_project(self) -> None:
        project_code = self._selected_project_code()
        if not project_code:
            QMessageBox.information(self, "No project", "Select a project first.")
            return
        project = self.repository.get_project_by_code(project_code)
        if not project:
            return

        session_count = self.repository.count_sessions_for_project(project_code)
        assigned_count = sum(1 for code in self._file_assignments.values() if code == project_code)
        label = project_display_name(project.name, project.project_code)
        message = f"Delete project '{label}'?"
        if session_count:
            message += f"\n\n{session_count} session(s) will be moved to unassigned."
        if assigned_count:
            message += f"\n\n{assigned_count} file assignment(s) will be removed."
        if project.is_locked:
            message += "\n\nThis project is locked for billing."
        message += "\n\nThis cannot be undone."

        answer = QMessageBox.question(
            self,
            "Delete project",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.repository.delete_project(project_code)
        except Exception as exc:
            QMessageBox.warning(self, "Unable to delete", str(exc))
            return

        for path, code in list(self._file_assignments.items()):
            if code == project_code:
                if self._on_unassign_file is not None:
                    self._on_unassign_file(path)
                else:
                    self._file_assignments.pop(path, None)

        self._notify_catalog_changed()
        self._refresh_projects()
