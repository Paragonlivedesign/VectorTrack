"""Review and import clients/projects from the shared sync catalog."""

from __future__ import annotations

import json
from typing import Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from vectortrack.budget import BudgetType
from vectortrack.db.repository import Repository
from vectortrack.services.catalog_sync import (
    CatalogApplyAction,
    CatalogApplyMode,
    CatalogDiffResult,
    CatalogItemKind,
    CatalogItemStatus,
    CatalogViewRow,
    apply_catalog_rows,
    build_catalog_view,
    import_remote_project,
    read_catalog,
)
from vectortrack.ui.layout_utils import configure_compact_table, scale_px


_STATUS_LABELS = {
    CatalogItemStatus.IN_SYNC: "In sync",
    CatalogItemStatus.REMOTE_ONLY: "Remote only",
    CatalogItemStatus.LOCAL_ONLY: "Local only",
    CatalogItemStatus.CONFLICT: "Conflict",
    CatalogItemStatus.SUGGESTED_DUPLICATE: "Suggested duplicate",
}


class CatalogSyncDialog(QDialog):
    catalog_changed = pyqtSignal()

    def __init__(
        self,
        repository: Repository,
        sync_folder: str,
        *,
        sync_enabled: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.sync_folder = sync_folder.strip()
        self.sync_enabled = sync_enabled
        self._catalog: dict = {}
        self._diff = CatalogDiffResult()
        self._row_by_id: dict[str, CatalogViewRow] = {}
        self._selected_rows: set[str] = set()

        self.setWindowTitle("Sync Catalog")
        self.resize(scale_px(980), scale_px(640))

        root = QVBoxLayout(self)
        self.notice_label = QLabel()
        self.notice_label.setWordWrap(True)
        self.notice_label.hide()
        root.addWidget(self.notice_label)

        toolbar = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All", "all")
        self.filter_combo.addItem("Remote only", "remote_only")
        self.filter_combo.addItem("Conflicts", "conflict")
        self.filter_combo.addItem("Suggestions", "suggested_duplicate")
        self.filter_combo.addItem("Clients", "client")
        self.filter_combo.addItem("Projects", "project")
        self.filter_combo.currentIndexChanged.connect(self._refresh_table)
        toolbar.addWidget(QLabel("Show"))
        toolbar.addWidget(self.filter_combo, 1)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._reload_catalog)
        import_selected_btn = QPushButton("Import Selected")
        import_selected_btn.clicked.connect(self._import_selected)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        toolbar.addWidget(refresh_btn)
        toolbar.addWidget(import_selected_btn)
        toolbar.addWidget(close_btn)
        root.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, 9, self)
        self.table.setHorizontalHeaderLabels(
            ["", "Type", "Code", "Name", "Client", "Rate", "Budget", "Status", "Actions"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._update_detail_panel)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        configure_compact_table(
            self.table,
            stretch_column=3,
            content_columns=[1, 2, 4, 5, 6, 7],
            fixed_columns={8: scale_px(220)},
        )
        splitter.addWidget(self.table)

        self.detail_panel = QTextEdit()
        self.detail_panel.setReadOnly(True)
        self.detail_panel.setPlaceholderText("Select a row to compare local vs remote details.")
        splitter.addWidget(self.detail_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        self._configure_availability()
        self._reload_catalog()

    def _configure_availability(self) -> None:
        if not self.sync_enabled or not self.sync_folder:
            self.notice_label.setText("Cross-machine sync is disabled or no sync folder is configured.")
            self.notice_label.show()
            self.table.setEnabled(False)
            return
        self.notice_label.hide()
        self.table.setEnabled(True)

    def _reload_catalog(self) -> None:
        if not self.sync_enabled or not self.sync_folder:
            return
        self._catalog = read_catalog(self.sync_folder)
        self._diff = build_catalog_view(self.repository, self._catalog)
        self._selected_rows.clear()
        self._refresh_table()

    def _passes_filter(self, row: CatalogViewRow) -> bool:
        filter_key = str(self.filter_combo.currentData() or "all")
        if filter_key == "all":
            return True
        if filter_key in {"client", "project"}:
            return row.kind.value == filter_key
        if filter_key == "remote_only":
            return row.status == CatalogItemStatus.REMOTE_ONLY
        if filter_key == "conflict":
            return row.status == CatalogItemStatus.CONFLICT
        if filter_key == "suggested_duplicate":
            return row.status == CatalogItemStatus.SUGGESTED_DUPLICATE
        return True

    def _display_name(self, row: CatalogViewRow) -> str:
        payload = row.remote or row.local or {}
        return str(payload.get("name") or row.key)

    def _display_client(self, row: CatalogViewRow) -> str:
        if row.kind == CatalogItemKind.CLIENT:
            payload = row.remote or row.local or {}
            return str(payload.get("code") or payload.get("name") or "")
        payload = row.remote or row.local or {}
        return str(payload.get("client_key") or "")

    def _display_rate(self, row: CatalogViewRow) -> str:
        if row.kind != CatalogItemKind.PROJECT:
            return ""
        payload = row.remote or row.local or {}
        rate = float(payload.get("hourly_rate") or 0.0)
        return f"${rate:.2f}" if rate else ""

    def _display_budget(self, row: CatalogViewRow) -> str:
        if row.kind != CatalogItemKind.PROJECT:
            return ""
        payload = row.remote or row.local or {}
        budget = payload.get("budget")
        if not isinstance(budget, dict):
            return ""
        amount = float(budget.get("amount") or 0.0)
        if amount <= 0:
            return ""
        if str(budget.get("type") or "") == BudgetType.MONEY.value:
            return f"${amount:.2f}"
        return f"{amount:.2f}h"

    def _refresh_table(self) -> None:
        self._row_by_id.clear()
        self.table.setRowCount(0)
        for row in self._diff.rows:
            if not self._passes_filter(row):
                continue
            table_row = self.table.rowCount()
            self.table.insertRow(table_row)
            self._row_by_id[row.row_id] = row

            check_item = QTableWidgetItem()
            check_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            if row.status == CatalogItemStatus.REMOTE_ONLY:
                check_item.setCheckState(
                    Qt.CheckState.Checked
                    if row.row_id in self._selected_rows
                    else Qt.CheckState.Unchecked
                )
            else:
                check_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            check_item.setData(Qt.ItemDataRole.UserRole, row.row_id)
            self.table.setItem(table_row, 0, check_item)

            values = [
                row.kind.value.title(),
                row.key,
                self._display_name(row),
                self._display_client(row),
                self._display_rate(row),
                self._display_budget(row),
                _STATUS_LABELS.get(row.status, row.status.value),
            ]
            for col, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                if col == 1:
                    item.setData(Qt.ItemDataRole.UserRole, row.row_id)
                self.table.setItem(table_row, col, item)

            self.table.setCellWidget(table_row, 8, self._action_widget(row))

    def _action_widget(self, row: CatalogViewRow) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(scale_px(4))

        def add_button(label: str, handler: Callable[[], None]) -> None:
            button = QPushButton(label)
            button.clicked.connect(handler)
            layout.addWidget(button)

        if row.status == CatalogItemStatus.REMOTE_ONLY and row.kind == CatalogItemKind.PROJECT:
            add_button("Import", lambda r=row: self._apply_action(r, CatalogApplyMode.IMPORT_REMOTE))
        elif row.status == CatalogItemStatus.REMOTE_ONLY and row.kind == CatalogItemKind.CLIENT:
            add_button("Import", lambda r=row: self._apply_action(r, CatalogApplyMode.IMPORT_AS_NEW_CLIENT))
        elif row.status == CatalogItemStatus.CONFLICT:
            add_button("Use Remote", lambda r=row: self._apply_action(r, CatalogApplyMode.USE_REMOTE))
            add_button("Keep Local", lambda r=row: self._apply_action(r, CatalogApplyMode.KEEP_LOCAL))
        elif row.status == CatalogItemStatus.SUGGESTED_DUPLICATE and row.kind == CatalogItemKind.CLIENT:
            add_button("Merge", lambda r=row: self._apply_action(r, CatalogApplyMode.MERGE_CLIENT))
            add_button("Import New", lambda r=row: self._apply_action(r, CatalogApplyMode.IMPORT_AS_NEW_CLIENT))
            add_button("Dismiss", lambda r=row: self._apply_action(r, CatalogApplyMode.DISMISS))

        layout.addStretch()
        return container

    def _apply_action(self, row: CatalogViewRow, mode: CatalogApplyMode) -> None:
        if mode == CatalogApplyMode.IMPORT_REMOTE and row.kind == CatalogItemKind.PROJECT:
            summary = import_remote_project(self.repository, self._catalog, row.key)
        else:
            summary = apply_catalog_rows(
                self.repository,
                self._catalog,
                [CatalogApplyAction(row=row, mode=mode)],
            )
        if summary.has_changes or mode in {CatalogApplyMode.KEEP_LOCAL, CatalogApplyMode.DISMISS}:
            self.catalog_changed.emit()
        self._reload_catalog()

    def _import_selected(self) -> None:
        actions: list[CatalogApplyAction] = []
        for table_row in range(self.table.rowCount()):
            check_item = self.table.item(table_row, 0)
            if check_item is None or check_item.checkState() != Qt.CheckState.Checked:
                continue
            row_id = str(check_item.data(Qt.ItemDataRole.UserRole) or "")
            row = self._row_by_id.get(row_id)
            if row is None or row.status != CatalogItemStatus.REMOTE_ONLY:
                continue
            mode = (
                CatalogApplyMode.IMPORT_AS_NEW_CLIENT
                if row.kind == CatalogItemKind.CLIENT
                else CatalogApplyMode.IMPORT_REMOTE
            )
            actions.append(CatalogApplyAction(row=row, mode=mode))
        if not actions:
            QMessageBox.information(self, "Nothing selected", "Select remote-only rows to import.")
            return
        summary = apply_catalog_rows(self.repository, self._catalog, actions)
        if summary.has_changes:
            self.catalog_changed.emit()
        self._reload_catalog()

    def _update_detail_panel(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            self.detail_panel.clear()
            return
        row_id = str(selected[0].data(Qt.ItemDataRole.UserRole) or "")
        row = self._row_by_id.get(row_id)
        if row is None:
            self.detail_panel.clear()
            return
        lines = [
            f"Type: {row.kind.value}",
            f"Key: {row.key}",
            f"Status: {_STATUS_LABELS.get(row.status, row.status.value)}",
        ]
        if row.similarity is not None:
            lines.append(f"Similarity: {row.similarity * 100:.0f}%")
        if row.suggested_local_key:
            lines.append(f"Suggested local match: {row.suggested_local_key}")
        if row.field_diffs:
            lines.append(f"Differs on: {', '.join(row.field_diffs)}")
        lines.append("")
        lines.append("Local:")
        lines.append(json.dumps(row.local or {}, indent=2))
        lines.append("")
        lines.append("Remote:")
        lines.append(json.dumps(row.remote or {}, indent=2))
        self.detail_panel.setPlainText("\n".join(lines))
