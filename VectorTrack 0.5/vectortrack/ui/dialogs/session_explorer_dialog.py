"""Drill-down session explorer for a file or billable project."""

from __future__ import annotations

import csv
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Callable, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from vectortrack.db.repository import Repository
from vectortrack.models import TimeSession
from vectortrack.services.report_data import ReportDataBuilder
from vectortrack.services.report_service import ReportService
from vectortrack.services.session_aggregator import SessionAggregator, UnifiedSession
from vectortrack.ui.dialogs.session_edit_dialog import SessionEditDialog
from vectortrack.ui.heatmap_widget import HeatmapWidget


class SessionExplorerDialog(QDialog):
    def __init__(
        self,
        repository: Repository,
        log_paths: list[str],
        mode: str,
        target: str,
        project_id: str,
        reload_callback: Callable[[], List[UnifiedSession]],
        report_service: Optional[ReportService] = None,
        data_builder: Optional[ReportDataBuilder] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.log_paths = log_paths
        self.mode = mode
        self.target = target
        self.project_id = project_id
        self.reload_callback = reload_callback
        self.report_service = report_service
        self.data_builder = data_builder
        self.sessions: List[UnifiedSession] = []
        self._day_filter: Optional[date] = None
        self._read_only = repository.is_project_locked(project_id)

        title_target = Path(target).name if mode == "file" else target
        self.setWindowTitle(f"Sessions: {title_target}")
        self.setMinimumSize(980, 640)

        root = QVBoxLayout(self)
        self.summary_label = QLabel("")
        root.addWidget(self.summary_label)

        self.tabs = QTabWidget(self)
        self.list_tab = QWidget(self)
        list_layout = QVBoxLayout(self.list_tab)
        self.table = QTableWidget(0, 9, self.list_tab)
        self.table.setHorizontalHeaderLabels(
            ["Start", "End", "Hours", "File", "Machine", "Source", "Amount", "Status", "Actions"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        list_layout.addWidget(self.table)
        self.tabs.addTab(self.list_tab, "List")

        self.calendar_tab = QWidget(self)
        calendar_layout = QVBoxLayout(self.calendar_tab)
        self.heatmap = HeatmapWidget(self.calendar_tab)
        self.heatmap.day_clicked.connect(self._on_day_clicked)
        calendar_layout.addWidget(self.heatmap)
        self.day_list = QTableWidget(0, 5, self.calendar_tab)
        self.day_list.setHorizontalHeaderLabels(["Start", "End", "Hours", "Machine", "Source"])
        self.day_list.verticalHeader().setVisible(False)
        calendar_layout.addWidget(self.day_list)
        self.tabs.addTab(self.calendar_tab, "Calendar")
        root.addWidget(self.tabs)

        self.conflict_label = QLabel("")
        root.addWidget(self.conflict_label)

        self.conflict_table = QTableWidget(0, 4, self)
        self.conflict_table.setHorizontalHeaderLabels(["Session A", "Session B", "Issue", "Actions"])
        self.conflict_table.verticalHeader().setVisible(False)
        self.conflict_table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.conflict_table)

        buttons = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export_csv)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(refresh_btn)
        buttons.addWidget(export_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

        self.refresh()

    def refresh(self) -> None:
        self.sessions = self.reload_callback()
        self._populate_summary()
        self._populate_table()
        self._populate_calendar()
        self._populate_conflicts()

    def _display_sessions(self) -> List[UnifiedSession]:
        sessions = list(self.sessions)
        if self._day_filter is not None:
            sessions = [session for session in sessions if session.start.date() == self._day_filter]
        return sessions

    def _active_sessions(self) -> List[UnifiedSession]:
        return [session for session in self._display_sessions() if not session.is_excluded]

    def _populate_summary(self) -> None:
        active = self._active_sessions()
        total_hours = sum(session.hours for session in active)
        machines = sorted({session.machine_id for session in active})
        conflicts = sum(1 for session in active if session.conflict_ids)
        excluded_count = sum(1 for session in self._display_sessions() if session.is_excluded)
        excluded_note = f" | Excluded: {excluded_count}" if excluded_count else ""
        self.summary_label.setText(
            f"Total: {total_hours:.2f} hrs | Sessions: {len(active)} | "
            f"Machines: {len(machines)} | Conflicts: {conflicts}{excluded_note}"
        )

    def _populate_table(self) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for session in self._display_sessions():
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                session.start.strftime("%Y-%m-%d %H:%M"),
                session.end.strftime("%Y-%m-%d %H:%M") if session.end else "Open",
                f"{session.hours:.2f}",
                session.file_alias,
                session.machine_id,
                session.source,
                f"${session.amount:.2f}",
                session.status,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, session.uid)
                if session.is_excluded:
                    item.setBackground(QBrush(QColor("#e8e8e8")))
                    item.setForeground(QBrush(QColor("#777777")))
                elif session.conflict_ids:
                    item.setBackground(QBrush(QColor("#f6deb2")))
                self.table.setItem(row, col, item)

            actions = QWidget(self.table)
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            if not self._read_only:
                if session.is_excluded:
                    restore_btn = QPushButton("Restore")
                    restore_btn.clicked.connect(
                        lambda _checked=False, uid=session.uid: self._restore_session(uid)
                    )
                    actions_layout.addWidget(restore_btn)
                else:
                    if session.is_editable:
                        edit_btn = QPushButton("Edit")
                        edit_btn.clicked.connect(
                            lambda _checked=False, uid=session.uid: self._edit_session(uid)
                        )
                        actions_layout.addWidget(edit_btn)
                    delete_btn = QPushButton(
                        "Delete" if session.source in {"live", "manual", "adjustment"} else "Exclude"
                    )
                    delete_btn.clicked.connect(
                        lambda _checked=False, uid=session.uid: self._delete_session(uid)
                    )
                    actions_layout.addWidget(delete_btn)
            self.table.setCellWidget(row, 8, actions)
        self.table.setSortingEnabled(True)

    def _populate_calendar(self) -> None:
        totals: dict[date, float] = {}
        for session in self.sessions:
            if session.is_excluded:
                continue
            day = session.start.date()
            totals[day] = totals.get(day, 0.0) + session.hours
        self.heatmap.set_day_values(totals)

        self.day_list.setRowCount(0)
        for session in self._display_sessions():
            row = self.day_list.rowCount()
            self.day_list.insertRow(row)
            for col, value in enumerate(
                [
                    session.start.strftime("%Y-%m-%d %H:%M"),
                    session.end.strftime("%Y-%m-%d %H:%M"),
                    f"{session.hours:.2f}",
                    session.machine_id,
                    session.source,
                ]
            ):
                item = QTableWidgetItem(value)
                if session.is_excluded:
                    item.setBackground(QBrush(QColor("#e8e8e8")))
                    item.setForeground(QBrush(QColor("#777777")))
                self.day_list.setItem(row, col, item)

    def _populate_conflicts(self) -> None:
        visible = [session for session in self.sessions if not session.is_excluded]
        pairs = []
        seen = set()
        for left in visible:
            for right_id in left.conflict_ids:
                if right_id.startswith("{"):
                    continue
                pair = tuple(sorted((left.uid, right_id)))
                if pair in seen:
                    continue
                right = next((item for item in visible if item.uid == right_id), None)
                if not right:
                    continue
                seen.add(pair)
                pairs.append((left, right))

        self.conflict_table.setRowCount(0)
        if not pairs:
            self.conflict_label.setText("No conflicts detected.")
            self.conflict_table.setVisible(False)
            return

        self.conflict_label.setText(f"{len(pairs)} overlapping session pair(s) detected.")
        self.conflict_table.setVisible(True)
        for left, right in pairs:
            row = self.conflict_table.rowCount()
            self.conflict_table.insertRow(row)
            self.conflict_table.setItem(
                row,
                0,
                QTableWidgetItem(
                    f"{left.machine_id}: {left.start.strftime('%m/%d %I:%M %p')} ({left.hours:.2f}h)"
                ),
            )
            self.conflict_table.setItem(
                row,
                1,
                QTableWidgetItem(
                    f"{right.machine_id}: {right.start.strftime('%m/%d %I:%M %p')} ({right.hours:.2f}h)"
                ),
            )
            self.conflict_table.setItem(row, 2, QTableWidgetItem("Overlapping time on same file"))

            actions = QWidget(self.conflict_table)
            layout = QHBoxLayout(actions)
            layout.setContentsMargins(2, 2, 2, 2)
            keep_a = QPushButton("Keep A")
            keep_b = QPushButton("Keep B")
            keep_both = QPushButton("Keep Both")
            merge_btn = QPushButton("Merge")
            keep_a.clicked.connect(lambda _checked=False, winner=left, loser=right: self._resolve_keep(winner, loser))
            keep_b.clicked.connect(lambda _checked=False, winner=right, loser=left: self._resolve_keep(winner, loser))
            keep_both.clicked.connect(
                lambda _checked=False, a=left, b=right: self._resolve_keep_both(a, b)
            )
            merge_btn.clicked.connect(lambda _checked=False, a=left, b=right: self._resolve_merge(a, b))
            if not self._read_only:
                layout.addWidget(keep_a)
                layout.addWidget(keep_b)
                layout.addWidget(keep_both)
                layout.addWidget(merge_btn)
            self.conflict_table.setCellWidget(row, 3, actions)

    def _session_by_uid(self, uid: str) -> Optional[UnifiedSession]:
        return next((session for session in self.sessions if session.uid == uid), None)

    def _edit_session(self, uid: str) -> None:
        session = self._session_by_uid(uid)
        if not session:
            return
        dialog = SessionEditDialog(session, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            if session.source in {"live", "manual"} and session.session_id is not None:
                existing = self.repository.get_session(session.session_id)
                if not existing:
                    return
                duration = values["end_time"] - values["start_time"]
                new_rate = float(values["hourly_rate"])
                rate_overridden = (
                    existing.rate_overridden
                    or abs(new_rate - existing.hourly_rate) > 0.001
                    or existing.source == "manual"
                )
                updated = TimeSession(
                    id=existing.id,
                    project_id=existing.project_id,
                    file_path=str(values["file_path"]),
                    file_alias=Path(str(values["file_path"])).name,
                    start_time=values["start_time"],
                    end_time=values["end_time"],
                    hourly_rate=new_rate,
                    rate_overridden=rate_overridden,
                    live_duration=duration if existing.source == "live" else existing.live_duration,
                    log_history_duration=existing.log_history_duration,
                    source=existing.source,
                    machine_id=existing.machine_id,
                )
                self.repository.update_session(updated)
            elif session.source == "adjustment" and session.adjustment_id is not None:
                self.repository.update_adjustment(
                    session.adjustment_id,
                    session.project_id,
                    str(values["file_path"]),
                    values["start_time"].isoformat(),
                    values["end_time"].isoformat(),
                    float(values["hourly_rate"]),
                    machine_id=session.machine_id,
                    notes=str(values.get("notes") or ""),
                    replaces_log_key=session.log_key,
                )
            elif session.source == "log":
                self.repository.add_adjustment(
                    project_id=session.project_id,
                    file_path=str(values["file_path"]),
                    start_time=values["start_time"].isoformat(),
                    end_time=values["end_time"].isoformat(),
                    hourly_rate=float(values["hourly_rate"]),
                    machine_id=session.machine_id,
                    notes="Edited from log session",
                    replaces_log_key=session.log_key,
                )
                if session.log_key:
                    self.repository.add_exclusion(
                        file_alias=session.file_alias,
                        start_time=session.start.isoformat(),
                        end_time=session.end.isoformat(),
                        machine_id=session.machine_id,
                        log_key=session.log_key,
                        reason="Replaced by adjustment",
                    )
        except (PermissionError, ValueError) as exc:
            QMessageBox.warning(self, "Edit Session", str(exc))
            return
        self.refresh()

    def _delete_session(self, uid: str) -> None:
        session = self._session_by_uid(uid)
        if not session:
            return
        try:
            if session.source in {"live", "manual"} and session.session_id is not None:
                self.repository.delete_session(session.session_id)
            elif session.source == "adjustment" and session.adjustment_id is not None:
                self.repository.delete_adjustment(session.adjustment_id)
            elif session.source == "log" and session.log_key:
                self.repository.add_exclusion(
                    file_alias=session.file_alias,
                    start_time=session.start.isoformat(),
                    end_time=session.end.isoformat(),
                    machine_id=session.machine_id,
                    log_key=session.log_key,
                    reason="Excluded by user",
                )
        except PermissionError as exc:
            QMessageBox.warning(self, "Delete Session", str(exc))
            return
        self.refresh()

    def _restore_session(self, uid: str) -> None:
        session = self._session_by_uid(uid)
        if not session:
            return
        if session.exclusion_id is not None:
            self.repository.delete_exclusion(session.exclusion_id)
        elif session.log_key:
            for row in self.repository.list_exclusions():
                if str(row.get("log_key") or "") == session.log_key:
                    self.repository.delete_exclusion(int(row["id"]))
                    break
        self.refresh()

    def _resolve_keep(self, winner: UnifiedSession, loser: UnifiedSession) -> None:
        if loser.log_key:
            self.repository.add_exclusion(
                file_alias=loser.file_alias,
                start_time=loser.start.isoformat(),
                end_time=loser.end.isoformat(),
                machine_id=loser.machine_id,
                log_key=loser.log_key,
                reason=f"Conflict resolved: kept {winner.machine_id}",
            )
            self.repository.set_conflict_resolution(loser.log_key, f"keep:{winner.machine_id}")
        self.refresh()

    def _resolve_keep_both(self, left: UnifiedSession, right: UnifiedSession) -> None:
        for session in (left, right):
            if session.log_key:
                self.repository.set_conflict_resolution(session.log_key, "keep_both")
        self.refresh()

    def _resolve_merge(self, left: UnifiedSession, right: UnifiedSession) -> None:
        start = min(left.start, right.start)
        end = max(left.end, right.end)
        rate = max(left.hourly_rate, right.hourly_rate)
        self.repository.add_adjustment(
            project_id=left.project_id,
            file_path=left.file_path,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            hourly_rate=rate,
            machine_id=f"{left.machine_id}+{right.machine_id}",
            notes="Merged conflict sessions",
        )
        for session in (left, right):
            if session.log_key:
                self.repository.add_exclusion(
                    file_alias=session.file_alias,
                    start_time=session.start.isoformat(),
                    end_time=session.end.isoformat(),
                    machine_id=session.machine_id,
                    log_key=session.log_key,
                    reason="Merged into adjustment",
                )
        self.refresh()

    def _on_day_clicked(self, selected_day: date) -> None:
        self._day_filter = selected_day
        self.tabs.setCurrentWidget(self.list_tab)
        self._populate_summary()
        self._populate_table()

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Sessions CSV",
            f"sessions_{self.target.replace('/', '_')}.csv",
            "CSV Files (*.csv)",
        )
        if not path:
            return
        sessions = self._active_sessions()
        if self.report_service is not None and self.data_builder is not None:
            rows = self.data_builder.rows_from_unified_sessions(sessions, self.project_id)
            active_rows = [row for row in rows if row.billable and not row.excluded]
            self.report_service.export_unified_csv(active_rows, path)
            QMessageBox.information(self, "Export complete", f"Saved:\n{path}")
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "date",
                    "client_name",
                    "project_name",
                    "project",
                    "file",
                    "raw_hours",
                    "billed_hours",
                    "rate",
                    "raw_amount",
                    "billed_amount",
                    "billable",
                ]
            )
            for session in sessions:
                billable = "no" if session.is_excluded or session.conflict_ids else "yes"
                writer.writerow(
                    [
                        session.start.strftime("%Y-%m-%d"),
                        "",
                        self.project_id,
                        self.project_id,
                        session.file_alias,
                        f"{session.hours:.2f}",
                        f"{session.hours:.2f}",
                        f"{session.hourly_rate:.2f}",
                        f"{session.amount:.2f}",
                        f"{session.amount:.2f}",
                        billable,
                    ]
                )
        QMessageBox.information(self, "Export complete", f"Saved:\n{path}")
