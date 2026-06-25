"""Clients tab with quick actions."""

from __future__ import annotations

from collections import defaultdict

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from vectortrack.db.repository import Repository
from vectortrack.ui.layout_utils import configure_compact_table, scale_px


class ClientsTab(QWidget):
    edit_client_requested = pyqtSignal(int)
    statement_requested = pyqtSignal(int)

    HEADERS = ["Client", "Code", "Status", "Projects", "Hours", "Billable", "Actions"]

    def __init__(self, repository: Repository, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.repository = repository
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, len(self.HEADERS), self)
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        configure_compact_table(
            self.table,
            stretch_column=0,
            content_columns=[1, 2, 3, 4, 5],
            fixed_columns={6: 180},
        )
        layout.addWidget(self.table, 1)

    def refresh(self) -> None:
        clients = self.repository.list_clients(active_only=False)
        projects = self.repository.list_projects(active_only=False)
        sessions = self.repository.list_sessions(include_open=True, limit=5000)

        project_to_client = {project.project_code: project.client_id for project in projects}
        projects_per_client: dict[int, int] = defaultdict(int)
        for project in projects:
            projects_per_client[int(project.client_id)] += 1

        hours_per_client: dict[int, float] = defaultdict(float)
        amount_per_client: dict[int, float] = defaultdict(float)
        for session in sessions:
            client_id = project_to_client.get(session.project_id)
            if client_id is None:
                continue
            hours_per_client[client_id] += session.active_duration.total_seconds() / 3600.0
            amount_per_client[client_id] += session.billable_amount

        self.table.setRowCount(0)
        for client in clients:
            row = self.table.rowCount()
            self.table.insertRow(row)
            client_id = int(client.id or 0)
            values = [
                client.name,
                client.code or "",
                "Active" if client.is_active else "Inactive",
                str(projects_per_client.get(client_id, 0)),
                f"{hours_per_client.get(client_id, 0.0):.2f}h",
                f"${amount_per_client.get(client_id, 0.0):.2f}",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(0x0100, client_id)  # Qt.UserRole
                self.table.setItem(row, col, item)

            actions = QWidget(self)
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(2, 1, 2, 1)
            action_layout.setSpacing(scale_px(4))
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda _checked=False, cid=client_id: self.edit_client_requested.emit(cid))
            statement_btn = QPushButton("Statement")
            statement_btn.clicked.connect(lambda _checked=False, cid=client_id: self.statement_requested.emit(cid))
            action_layout.addWidget(edit_btn)
            action_layout.addWidget(statement_btn)
            self.table.setCellWidget(row, len(self.HEADERS) - 1, actions)

    def selected_client_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = item.data(0x0100)
        return int(value) if value else None
