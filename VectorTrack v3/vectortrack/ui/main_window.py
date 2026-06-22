"""VectorTrack v4 main window."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from vectortrack import config
from vectortrack.activity_monitor import ActivityMonitor
from vectortrack.config import ENFORCE_LICENSING
from vectortrack.db.repository import Repository
from vectortrack.models import TimeSession
from vectortrack.process_monitor import ProcessMonitor
from vectortrack.services.backup_service import BackupService
from vectortrack.services.billing_service import BillingContext, BillingService
from vectortrack.services.import_export import ImportExportService
from vectortrack.services.log_service import LogService
from vectortrack.services.report_service import ReportService
from vectortrack.services.autostart import set_enabled as set_autostart_enabled
from vectortrack.services.hotkey_service import HotkeyService
from vectortrack.services.notification_service import NotificationService
from vectortrack.services.tracking_service import TrackingService
from vectortrack.ui.clients_tab import ClientsTab
from vectortrack.ui.dashboard_strip import DashboardStrip
from vectortrack.ui.heatmap_widget import HeatmapWidget
from vectortrack.ui.history_browser import HistoryBrowser
from vectortrack.ui.hud_window import HUDWindow
from vectortrack.ui.open_files_table import OpenFilesTable
from vectortrack.ui.project_summary_table import ProjectSummaryTable
from vectortrack.ui.theme import apply_theme
from vectortrack.ui.tray import VectorTrackTray
from vectortrack.ui.dialogs.about_dialog import AboutDialog
from vectortrack.ui.dialogs.backup_restore_dialog import BackupRestoreDialog
from vectortrack.ui.dialogs.bug_report_dialog import BugReportDialog
from vectortrack.ui.dialogs.client_editor_dialog import ClientEditorDialog
from vectortrack.ui.dialogs.donate_dialog import DonateDialog
from vectortrack.ui.dialogs.first_run_wizard import FirstRunWizard
from vectortrack.ui.dialogs.import_bundle_dialog import ImportBundleDialog
from vectortrack.ui.dialogs.log_library_dialog import LogLibraryDialog
from vectortrack.ui.dialogs.manual_entry_dialog import ManualEntryDialog
from vectortrack.ui.dialogs.project_assign_dialog import ProjectAssignDialog
from vectortrack.ui.dialogs.project_editor_dialog import ProjectEditorDialog
from vectortrack.ui.dialogs.report_dialog import ReportDialog
from vectortrack.ui.dialogs.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    SUPPORT_EMAIL = "Info@paragonlivedesign.com"

    def __init__(
        self,
        repository: Repository,
        tracking_service: TrackingService,
        log_service: LogService,
        billing_service: BillingService,
        process_monitor: ProcessMonitor,
        activity_monitor: ActivityMonitor,
    ) -> None:
        super().__init__()
        self.repository = repository
        self.tracking_service = tracking_service
        self.log_service = log_service
        self.billing_service = billing_service
        self.process_monitor = process_monitor
        self.activity_monitor = activity_monitor
        self.report_service = ReportService(output_dir="reports")
        self.backup_service = BackupService(
            backup_dir=str(config.resolve_data_dir() / "backups"),
            retention_count=config.BACKUP_RETENTION_COUNT,
        )
        self.import_export_service = ImportExportService()

        self.settings = QSettings("Paragon", "VectorTrack")
        if self.settings.value("minimize_to_tray") is None:
            self.settings.setValue("minimize_to_tray", True)
        self.auto_track_enabled = self.settings.value("auto_track_enabled", True, type=bool)
        self.import_vw_log_history = self.settings.value("import_vw_log_history", True, type=bool)
        self.vw_log_merge_years = self.settings.value("vw_log_merge_years", True, type=bool)
        self.vw_log_path = self.settings.value("vw_log_path", "", type=str)
        self.dark_mode_enabled = self.settings.value("dark_mode_enabled", False, type=bool)
        self.default_rate = self.settings.value("default_hourly_rate", 75.0, type=float)
        self.minimize_to_tray = self.settings.value("minimize_to_tray", True, type=bool)
        self.notifications_enabled = self.settings.value("notifications_enabled", True, type=bool)
        self.global_hotkeys_enabled = self.settings.value("global_hotkeys_enabled", True, type=bool)
        self.eod_notify_enabled = self.settings.value("eod_notify_enabled", True, type=bool)
        self.eod_notify_hour = int(self.settings.value("eod_notify_hour", 17, type=int))
        self.log_cache: dict[str, dict[str, float | datetime]] = {}
        self.file_project_overrides: dict[str, str] = self._load_project_overrides()
        self._last_log_sync = datetime.min
        self._last_rows: list[dict[str, object]] = []
        self._is_quitting = False
        self._known_open_files: set[str] = set()
        self._budget_notified: dict[str, str] = {}
        self._delta_notified: dict[str, float] = {}
        self._idle_notified = False
        self._eod_notified_date: date | None = None
        self.notification_service = NotificationService(enabled=self.notifications_enabled)
        self.hotkey_service = HotkeyService(
            enabled=self.global_hotkeys_enabled and os.environ.get("VECTORTRACK_TESTING") != "1"
        )

        self.setWindowTitle("VectorTrack")
        self.setMinimumSize(1000, 680)
        self.resize(1320, 820)

        self.tray = VectorTrackTray(self)
        self.tray.show()
        self.hud = HUDWindow(self)
        self.hud.hide()

        self._build_ui()
        self._create_actions()
        self._build_toolbar()
        self._build_menus()
        self._build_statusbar()
        self._restore_window_geometry()
        self._auto_detect_vectorworks()
        self._apply_saved_theme()
        self._write_paths_manifest()

        self.tracking_service.start()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._tick)
        self.update_timer.start(1000)
        self.history_browser.refresh_requested.connect(self._refresh_history)
        self.open_files_table.assign_project_requested.connect(self._assign_project)
        self.open_files_table.manual_entry_requested.connect(self._open_manual_entry)
        self.heatmap_widget.day_clicked.connect(self._jump_history_to_day)
        self.clients_tab.edit_client_requested.connect(self._open_client_editor)
        self.clients_tab.statement_requested.connect(self._generate_client_statement)

        self._setup_hotkeys()
        self._setup_notifications()
        self.hotkey_service.start()

        QTimer.singleShot(50, self._show_first_run_wizard_if_needed)
        QTimer.singleShot(0, self._tick)
        QTimer.singleShot(150, self._refresh_history)

    @classmethod
    def create_default(cls) -> "MainWindow":
        repository = Repository()
        process_monitor = ProcessMonitor()
        activity_monitor = ActivityMonitor(
            idle_timeout_seconds=60
            * int(QSettings("Paragon", "VectorTrack").value("default_idle_timeout", 5, type=int))
        )
        tracking = TrackingService(
            process_monitor=process_monitor,
            activity_monitor=activity_monitor,
            repository=repository,
        )
        return cls(
            repository=repository,
            tracking_service=tracking,
            log_service=LogService(),
            billing_service=BillingService(),
            process_monitor=process_monitor,
            activity_monitor=activity_monitor,
        )

    def _build_ui(self) -> None:
        container = QWidget(self)
        root = QVBoxLayout(container)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        self.setCentralWidget(container)

        self.dashboard_strip = DashboardStrip(container)
        root.addWidget(self.dashboard_strip)

        splitter = QSplitter(Qt.Orientation.Vertical, container)
        root.addWidget(splitter, 1)

        top_panel = QWidget(splitter)
        top_layout = QVBoxLayout(top_panel)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)
        self.open_files_table = OpenFilesTable(top_panel)
        self.project_summary_table = ProjectSummaryTable(top_panel)
        self.open_files_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_summary_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.open_files_table.customContextMenuRequested.connect(self._show_open_files_context_menu)
        self.project_summary_table.customContextMenuRequested.connect(self._show_project_summary_context_menu)
        top_layout.addWidget(self.open_files_table, 2)
        top_layout.addWidget(self.project_summary_table, 1)
        splitter.addWidget(top_panel)

        self.bottom_tabs = QTabWidget(splitter)
        self.history_browser = HistoryBrowser(self.bottom_tabs)
        self.heatmap_widget = HeatmapWidget(self.bottom_tabs)
        self.clients_tab = ClientsTab(self.repository, self.bottom_tabs)
        self.bottom_tabs.addTab(self.history_browser, "History")
        self.bottom_tabs.addTab(self.heatmap_widget, "Heatmap")
        self.bottom_tabs.addTab(self.clients_tab, "Clients")
        splitter.addWidget(self.bottom_tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

    def _create_actions(self) -> None:
        self.pause_action = QAction("Pause Tracking", self)
        self.pause_action.setShortcut("Ctrl+P")
        self.pause_action.setCheckable(True)
        self.pause_action.setChecked(self.tracking_service.is_paused)
        self.pause_action.toggled.connect(self._set_pause_state)

        self.meeting_action = QAction("Start 30m Meeting", self)
        self.meeting_action.setShortcut("Ctrl+M")
        self.meeting_action.triggered.connect(self._toggle_meeting_mode)

        self.refresh_action = QAction("Refresh", self)
        self.refresh_action.setShortcut("F5")
        self.refresh_action.triggered.connect(self._tick)

        self.report_action = QAction("Generate Report...", self)
        self.report_action.setShortcut("Ctrl+R")
        self.report_action.triggered.connect(self._open_report_dialog)

        self.settings_action = QAction("Settings...", self)
        self.settings_action.setShortcut("Ctrl+,")
        self.settings_action.triggered.connect(self._show_settings)

        self.hud_action = QAction("HUD", self)
        self.hud_action.setCheckable(True)
        self.hud_action.toggled.connect(self.hud.setVisible)

        self.exit_action = QAction("Exit", self)
        self.exit_action.triggered.connect(self._quit_app)

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.addAction(self.pause_action)
        toolbar.addAction(self.meeting_action)
        toolbar.addAction(self.refresh_action)
        toolbar.addAction(self.report_action)
        toolbar.addSeparator()
        toolbar.addAction(self.hud_action)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("Import Bundle...", self._open_import_bundle_dialog)
        file_menu.addAction("Backup / Restore...", self._open_backup_restore_dialog)
        file_menu.addSeparator()
        file_menu.addAction("Select Vectorworks EXE...", self._select_vectorworks_exe)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        edit_menu = self.menuBar().addMenu("Edit")
        edit_menu.addAction(self.settings_action)
        edit_menu.addAction("Manual Entry...", lambda: self._open_manual_entry(""))
        edit_menu.addAction("Project Editor...", self._show_project_editor)
        edit_menu.addAction("Client Editor...", lambda: self._open_client_editor(None))
        edit_menu.addAction("Log Library...", self._open_log_library_dialog)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(self.pause_action)
        view_menu.addAction(self.meeting_action)
        view_menu.addAction(self.refresh_action)
        view_menu.addAction(self.hud_action)
        view_menu.addSeparator()
        view_menu.addAction("Show History", lambda: self.bottom_tabs.setCurrentWidget(self.history_browser))
        view_menu.addAction("Show Heatmap", lambda: self.bottom_tabs.setCurrentWidget(self.heatmap_widget))
        view_menu.addAction("Show Clients", lambda: self.bottom_tabs.setCurrentWidget(self.clients_tab))

        reports_menu = self.menuBar().addMenu("Reports")
        reports_menu.addAction(self.report_action)
        reports_menu.addAction("Export Master PDF", self._export_master_report)
        reports_menu.addAction("Generate Selected Project PDF", self._report_selected_project)

        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction("Report a Bug...", self._show_bug_report_dialog)
        help_menu.addAction("Contact Support", self._contact_support)
        help_menu.addSeparator()
        help_menu.addAction("About", self._show_about)
        help_menu.addAction("Donate", self._show_donate)

    def _build_statusbar(self) -> None:
        status = QStatusBar(self)
        status.showMessage("Ready")
        self.setStatusBar(status)

    def _apply_saved_theme(self) -> None:
        mode = "dark" if self.dark_mode_enabled else "light"
        apply_theme(QApplication.instance(), mode=mode)

    def _show_first_run_wizard_if_needed(self) -> None:
        if self.settings.value("wizard_completed", False, type=bool):
            return
        wizard = FirstRunWizard(self.settings, self)
        wizard.exec()
        self.import_vw_log_history = self.settings.value("import_vw_log_history", True, type=bool)
        self.vw_log_merge_years = self.settings.value("vw_log_merge_years", True, type=bool)
        self.auto_track_enabled = self.settings.value("auto_track_enabled", True, type=bool)
        self.dark_mode_enabled = self.settings.value("dark_mode_enabled", False, type=bool)
        self.minimize_to_tray = self.settings.value("minimize_to_tray", True, type=bool)
        self._apply_saved_theme()

    def _write_paths_manifest(self) -> None:
        try:
            config.write_paths_json(
                {
                    "vectorworks_path": self.settings.value("vectorworks_path", "", type=str),
                    "vw_log_path": self.vw_log_path,
                }
            )
        except Exception:
            # Manifest writing is best-effort and should not interrupt UI startup.
            pass

    def _auto_detect_vectorworks(self) -> None:
        saved = self.settings.value("vectorworks_path", "", type=str)
        if saved and os.path.exists(saved):
            try:
                self.process_monitor.set_vectorworks_path(saved)
                return
            except Exception:
                pass
        path = self.process_monitor.auto_select_vectorworks()
        if path:
            self.settings.setValue("vectorworks_path", path)
            self._write_paths_manifest()

    def _select_vectorworks_exe(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Vectorworks executable",
            "",
            "Executable (*.exe);;All files (*)",
        )
        if not file_path:
            return
        try:
            self.process_monitor.set_vectorworks_path(file_path)
            self.settings.setValue("vectorworks_path", file_path)
            self._write_paths_manifest()
            self._tick()
        except Exception as exc:
            QMessageBox.warning(self, "Vectorworks path error", str(exc))

    def _load_project_overrides(self) -> dict[str, str]:
        raw = self.settings.value("file_project_overrides", "{}", type=str)
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
        return {}

    def _save_project_overrides(self) -> None:
        self.settings.setValue("file_project_overrides", json.dumps(self.file_project_overrides))

    def _active_log_paths(self) -> list[str]:
        extra_paths = [
            str(source.get("source", "")).strip()
            for source in self.repository.list_log_sources()
            if str(source.get("source", "")).strip()
        ]
        paths, _desc = self.log_service.resolve_sources(
            vw_exe_path=self.process_monitor.vectorworks_path,
            manual_log_path=self.vw_log_path or None,
            merge_other_years=self.vw_log_merge_years,
            extra_paths=extra_paths,
        )
        return paths

    def _log_stats_for_file(self, file_path: str, project_name: str) -> tuple[float, float]:
        if not self.import_vw_log_history:
            return 0.0, 0.0
        cached = self.log_cache.get(file_path)
        if cached and isinstance(cached.get("synced_at"), datetime):
            if (datetime.now() - cached["synced_at"]).total_seconds() < 60:
                return float(cached["closed_hours"]), float(cached["open_hours"])
        summary = self.log_service.get_project_summary(
            project_name=project_name,
            log_paths=self._active_log_paths(),
            aliases=[os.path.basename(file_path)],
        )
        self.log_cache[file_path] = {
            "closed_hours": summary.closed_hours,
            "open_hours": summary.open_hours,
            "synced_at": datetime.now(),
        }
        return summary.closed_hours, summary.open_hours

    def _rate_for_project(self, project_code: str) -> float:
        project = self.repository.get_project_by_code(project_code)
        return float(project.hourly_rate) if project else self.default_rate

    def _budget_for_project(self, project_code: str) -> float:
        raw = self.repository.get_setting(f"budget_hours:{project_code}", "0")
        try:
            return max(0.0, float(raw or 0.0))
        except Exception:
            return 0.0

    def _setup_hotkeys(self) -> None:
        def toggle_pause() -> None:
            self.pause_action.setChecked(not self.pause_action.isChecked())

        self.hotkey_service.register_callback("p", toggle_pause)
        self.hotkey_service.register_callback("m", self._toggle_meeting_mode)
        self.hotkey_service.register_callback("r", self._tick)
        self.hotkey_service.register_callback("h", lambda: self.hud_action.toggle())

    def _setup_notifications(self) -> None:
        self.activity_monitor.add_activity_callback(self._on_activity_state_changed)

    def _on_activity_state_changed(self, is_active: bool) -> None:
        if is_active:
            self._idle_notified = False
            return
        if self._idle_notified or not self.notifications_enabled:
            return
        current = self.tracking_service.current_state
        if not current:
            return
        self._idle_notified = True
        idle_minutes = max(1, int(self.activity_monitor.idle_timeout.total_seconds() // 60))
        self.notification_service.notify_idle(os.path.basename(current.file_path), idle_minutes)

    def _check_workflow_notifications(self, rows: list[dict[str, object]]) -> None:
        if not self.notifications_enabled:
            return

        current_paths = {str(row["file_path"]) for row in rows}
        for closed_path in self._known_open_files - current_paths:
            self.notification_service.notify_file_closed(os.path.basename(closed_path))
        self._known_open_files = current_paths

        for row in rows:
            delta = float(row.get("delta_hours", 0.0))
            file_path = str(row["file_path"])
            if abs(delta) >= 0.5:
                previous = self._delta_notified.get(file_path, 0.0)
                if abs(delta - previous) >= 0.5:
                    self.notification_service.notify_log_delta(str(row["file_name"]), delta)
                    self._delta_notified[file_path] = delta

        for row in rows:
            project = str(row["project"])
            budget = self._budget_for_project(project)
            if budget <= 0:
                continue
            tracked = float(row["past_hours"]) + float(row["live_hours"])
            ratio = tracked / budget
            level = "100" if ratio >= 1.0 else "80" if ratio >= config.BUDGET_WARN_PERCENT else ""
            if not level or self._budget_notified.get(project) == level:
                continue
            if level == "80" and self._budget_notified.get(project) == "100":
                continue
            self._budget_notified[project] = level
            self.notification_service.notify_budget_warning(project, ratio * 100.0)

        now = datetime.now()
        if (
            self.eod_notify_enabled
            and now.hour == self.eod_notify_hour
            and now.minute == 0
            and self._eod_notified_date != now.date()
        ):
            sessions = self.repository.list_sessions(limit=5000)
            today_hours = sum(
                session.active_duration.total_seconds() / 3600.0
                for session in sessions
                if session.start_time.date() == now.date()
            )
            today_amount = sum(
                session.billable_amount
                for session in sessions
                if session.start_time.date() == now.date()
            )
            self.notification_service.notify_eod(today_hours, today_amount)
            self._eod_notified_date = now.date()

    def _rows_from_tracking(self) -> list[dict[str, object]]:
        windows = self.process_monitor.refresh()
        open_paths = {window.file_path for window in windows if window.file_path}
        rows: list[dict[str, object]] = []
        for file_path in sorted(open_paths):
            state = self.tracking_service.states_by_file.get(file_path)
            fallback_project = Path(file_path).stem
            project_code = self.file_project_overrides.get(file_path) or (
                state.project_id if state else fallback_project
            )
            rate = self._rate_for_project(project_code)
            live_hours = float(state.tracked_hours if state else 0.0)
            closed_hours, open_hours = self._log_stats_for_file(file_path, Path(file_path).name)
            delta_hours = open_hours - live_hours
            billing = self.billing_service.compute(
                BillingContext(
                    rate=rate,
                    duration_hours=max(0.0, closed_hours + live_hours),
                    started_at=(state.started_at if state else None),
                )
            )
            status = "Tracking"
            if self.tracking_service.is_paused and state is self.tracking_service.current_state:
                status = "Paused"
            elif state is None:
                status = "Open"
            rows.append(
                {
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "project": project_code,
                    "status": status,
                    "past_hours": closed_hours,
                    "live_hours": live_hours,
                    "delta_hours": delta_hours,
                    "rate": rate,
                    "earned": billing.total_due,
                }
            )
        return rows

    def _tick(self) -> None:
        if not self.process_monitor.vectorworks_path:
            self.statusBar().showMessage("Vectorworks executable not set")
            return
        self.tracking_service.tick()
        rows = self._rows_from_tracking()
        self._last_rows = rows
        self.open_files_table.set_rows(rows)
        self._refresh_project_summary(rows)
        self._refresh_dash_metrics(rows)
        self._refresh_hud(rows)
        self._check_workflow_notifications(rows)
        if (datetime.now() - self._last_log_sync) > timedelta(seconds=60):
            self._last_log_sync = datetime.now()
            self._refresh_history()

    def _refresh_project_summary(self, rows: list[dict[str, object]]) -> None:
        per_project: dict[str, dict[str, float]] = {}
        for row in rows:
            project = str(row["project"])
            agg = per_project.setdefault(
                project,
                {
                    "tracked_hours": 0.0,
                    "billable": 0.0,
                    "rate": float(row["rate"]),
                },
            )
            agg["tracked_hours"] += float(row["past_hours"]) + float(row["live_hours"])
            agg["billable"] += float(row["earned"])
        self.project_summary_table.set_rows(
            [
                {
                    "project": key,
                    **vals,
                    "budget_hours": self._budget_for_project(key),
                }
                for key, vals in sorted(per_project.items())
            ]
        )

    def _refresh_dash_metrics(self, rows: list[dict[str, object]]) -> None:
        total_hours = sum(float(row["past_hours"]) + float(row["live_hours"]) for row in rows)
        total_earned = sum(float(row["earned"]) for row in rows)
        sessions = self.repository.list_sessions(limit=2000)
        now = datetime.now()
        today_hours = 0.0
        week_hours = 0.0
        month_hours = 0.0
        for session in sessions:
            hours = session.active_duration.total_seconds() / 3600.0
            if session.start_time.date() == now.date():
                today_hours += hours
            if session.start_time.isocalendar()[:2] == now.isocalendar()[:2]:
                week_hours += hours
            if session.start_time.year == now.year and session.start_time.month == now.month:
                month_hours += hours
        self.dashboard_strip.set_metrics(
            today_hours=today_hours,
            week_hours=week_hours,
            month_hours=max(month_hours, total_hours),
            earned=total_earned,
        )

    def _refresh_hud(self, rows: list[dict[str, object]]) -> None:
        current = self.tracking_service.current_state
        if not current:
            self.hud.set_stats("No active file", 0.0, 0.0)
            return
        row = next((item for item in rows if item["file_path"] == current.file_path), None)
        earned = float(row["earned"]) if row else 0.0
        self.hud.set_stats(os.path.basename(current.file_path), float(current.tracked_hours), earned)

    def _refresh_history(self) -> None:
        selected_project = self.history_browser.selected_project()
        sessions = self.repository.list_sessions(project_id=selected_project or None, include_open=True, limit=5000)
        start_limit = self.history_browser.from_filter.dateTime().toPyDateTime()
        end_limit = self.history_browser.to_filter.dateTime().toPyDateTime()
        rows = []
        for session in sessions:
            if session.start_time < start_limit or session.start_time > end_limit:
                continue
            file_label = self._session_file_label(session)
            project_label = session.project_id
            if self.repository.is_project_locked(session.project_id):
                project_label = f"{project_label} [LOCKED]"
            rows.append(
                {
                    "start": session.start_time.strftime("%Y-%m-%d %H:%M"),
                    "end": session.end_time.strftime("%Y-%m-%d %H:%M") if session.end_time else "Open",
                    "project": project_label,
                    "file": file_label,
                    "hours": session.active_duration.total_seconds() / 3600.0,
                    "rate": session.hourly_rate,
                    "amount": session.billable_amount,
                }
            )
        self.history_browser.set_rows(rows)
        self.history_browser.set_project_options([project.project_code for project in self.repository.list_projects()])
        self._refresh_heatmap()
        self.clients_tab.refresh()

    def _refresh_heatmap(self) -> None:
        sessions = self.repository.list_sessions(include_open=True, limit=15000)
        totals: dict[date, float] = {}
        for session in sessions:
            day = session.start_time.date()
            totals[day] = totals.get(day, 0.0) + (session.active_duration.total_seconds() / 3600.0)
        self.heatmap_widget.set_day_values(totals)

    def _jump_history_to_day(self, selected_day: date) -> None:
        day_start = datetime.combine(selected_day, time.min)
        day_end = day_start + timedelta(days=1) - timedelta(seconds=1)
        self.history_browser.from_filter.setDateTime(day_start)
        self.history_browser.to_filter.setDateTime(day_end)
        self.bottom_tabs.setCurrentWidget(self.history_browser)
        self._refresh_history()

    def _assign_project(self, file_path: str) -> None:
        projects = [project.project_code for project in self.repository.list_projects()]
        if not projects:
            QMessageBox.information(self, "No projects", "Create a project first in Project Editor.")
            return
        dialog = ProjectAssignDialog(file_path=file_path, projects=projects, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        project_code = dialog.selected_project()
        if not project_code:
            return
        self.file_project_overrides[file_path] = project_code
        state = self.tracking_service.states_by_file.get(file_path)
        if state is not None:
            state.project_id = project_code
            self.repository.update_session_duration(state, 0.0)
        self._save_project_overrides()
        self._tick()

    def _open_manual_entry(self, suggested_file: str) -> None:
        projects = [project.project_code for project in self.repository.list_projects()]
        dialog = ManualEntryDialog(
            projects=projects,
            suggested_file=suggested_file,
            default_rate=self.default_rate,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        values = dialog.values()
        start_time = values["start_time"]
        end_time = values["end_time"]
        if not isinstance(start_time, datetime) or not isinstance(end_time, datetime) or end_time <= start_time:
            QMessageBox.warning(self, "Invalid range", "End time must be after start time.")
            return
        duration = end_time - start_time
        project_code = str(values["project_id"])
        session = TimeSession(
            project_id=project_code,
            file_path=str(values["file_path"]),
            start_time=start_time,
            end_time=end_time,
            hourly_rate=float(values["hourly_rate"]),
            live_duration=duration,
            source="manual",
        )
        try:
            self.repository.add_manual_session(session)
        except PermissionError as exc:
            QMessageBox.warning(self, "Project locked", str(exc))
            return
        self._refresh_history()

    @staticmethod
    def _session_file_label(session: TimeSession) -> str:
        name = os.path.basename(session.file_path)
        if session.source == "manual":
            return f"{name}*"
        return name

    def _show_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        values = dialog.values()
        for key, value in values.items():
            self.settings.setValue(key, value)
        self.auto_track_enabled = bool(values["auto_track_enabled"])
        self.import_vw_log_history = bool(values["import_vw_log_history"])
        self.vw_log_merge_years = bool(values["vw_log_merge_years"])
        self.dark_mode_enabled = bool(values["dark_mode_enabled"])
        self.default_rate = float(values["default_hourly_rate"])
        self.minimize_to_tray = bool(values["minimize_to_tray"])
        self.notifications_enabled = bool(values.get("notifications_enabled", True))
        self.global_hotkeys_enabled = bool(values.get("global_hotkeys_enabled", True))
        self.eod_notify_enabled = bool(values.get("eod_notify_enabled", True))
        self.eod_notify_hour = int(values.get("eod_notify_hour", 17))
        self.notification_service.set_enabled(self.notifications_enabled)
        self.hotkey_service.set_enabled(
            self.global_hotkeys_enabled and os.environ.get("VECTORTRACK_TESTING") != "1"
        )
        if values.get("portable_mode") is not None:
            config.set_portable_mode(bool(values["portable_mode"]))
        try:
            set_autostart_enabled(bool(values.get("autostart_enabled", False)))
        except OSError as exc:
            QMessageBox.warning(self, "Autostart", f"Could not update Windows startup entry:\n{exc}")
        self.activity_monitor.set_idle_timeout(int(values["default_idle_timeout"]) * 60)
        self._apply_saved_theme()
        self._write_paths_manifest()
        self._tick()

    def _show_project_editor(self) -> None:
        ProjectEditorDialog(self.repository, self).exec()
        self._refresh_history()

    def _show_about(self) -> None:
        AboutDialog(self).exec()

    def _show_donate(self) -> None:
        DonateDialog(self).exec()

    def _open_client_editor(self, client_id: int | None) -> None:
        dialog = ClientEditorDialog(self.repository, client_id=client_id, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.clients_tab.refresh()

    def _generate_client_statement(self, client_id: int) -> None:
        client = self.repository.get_client(client_id)
        if client is None:
            QMessageBox.warning(self, "Client missing", "The selected client no longer exists.")
            return
        projects = self.repository.list_projects(client_id=client_id, active_only=False)
        if not projects:
            QMessageBox.information(self, "No projects", "No projects are assigned to this client.")
            return
        by_project = {project.project_code: project for project in projects}
        line_items: list[dict[str, object]] = []
        for session in self.repository.list_sessions(include_open=True, limit=15000):
            project = by_project.get(session.project_id)
            if project is None:
                continue
            line_items.append(
                {
                    "description": f"{project.project_code} - {os.path.basename(session.file_path)}",
                    "hours": session.active_duration.total_seconds() / 3600.0,
                    "rate": session.hourly_rate,
                    "amount": session.billable_amount,
                }
            )
        if not line_items:
            QMessageBox.information(self, "No data", "No session entries found for this client.")
            return
        output_path = self.report_service.create_client_statement(client.name, line_items)
        QMessageBox.information(self, "Statement generated", f"Saved:\n{output_path}")
        QDesktopServices.openUrl(QUrl.fromLocalFile(output_path))

    def _open_log_library_dialog(self) -> None:
        LogLibraryDialog(self.repository, self).exec()
        self.log_cache.clear()
        self._tick()

    def _open_import_bundle_dialog(self) -> None:
        dialog = ImportBundleDialog(self.repository, self.import_export_service, self)
        dialog.imported.connect(lambda _count: self._refresh_history())
        dialog.exec()

    def _open_backup_restore_dialog(self) -> None:
        BackupRestoreDialog(self.backup_service, self).exec()

    def _open_report_dialog(self) -> None:
        ReportDialog(self.repository, self.report_service, self).exec()

    def _show_bug_report_dialog(self) -> None:
        BugReportDialog(self).exec()

    def _contact_support(self) -> None:
        QDesktopServices.openUrl(QUrl(f"mailto:{self.SUPPORT_EMAIL}"))

    def _set_pause_state(self, paused: bool) -> None:
        self.tracking_service.set_paused(paused)
        self.statusBar().showMessage("Tracking paused" if paused else "Tracking resumed", 2500)
        self._tick()

    def _toggle_meeting_mode(self) -> None:
        if self.tracking_service.meeting_topic:
            self.tracking_service.disable_meeting_mode()
            self.statusBar().showMessage("Meeting mode ended", 2500)
            self._tick()
            return
        self.tracking_service.enable_meeting_mode("Meeting")
        self.statusBar().showMessage("Meeting mode started for 30 minutes", 3000)
        self._tick()

    def _report_selected_project(self) -> None:
        row = self.project_summary_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No project selected", "Select a project in the summary table first.")
            return
        project_code = self.project_summary_table.project_code_for_row(row)
        if not project_code:
            QMessageBox.warning(self, "Selection error", "Unable to resolve project code.")
            return
        self._generate_project_report(project_code)

    def _generate_project_report(self, project_code: str) -> None:
        rows = []
        for session in self.repository.list_sessions(project_id=project_code, include_open=True, limit=15000):
            rows.append(
                {
                    "date": session.start_time.strftime("%Y-%m-%d"),
                    "file": self._session_file_label(session),
                    "hours": session.active_duration.total_seconds() / 3600.0,
                    "rate": session.hourly_rate,
                    "amount": session.billable_amount,
                }
            )
        if not rows:
            QMessageBox.information(self, "No data", f"No rows available for project '{project_code}'.")
            return
        output = self.report_service.create_project_pdf(project_code, rows)
        QMessageBox.information(self, "Report created", f"Saved report to:\n{output}")

    def _show_open_files_context_menu(self, pos) -> None:
        row = self.open_files_table.rowAt(pos.y())
        if row < 0:
            return
        file_path = self.open_files_table.file_path_for_row(row)
        project_code = self.open_files_table.item(row, 1).text() if self.open_files_table.item(row, 1) else ""
        menu = QMenu(self)
        menu.addAction("Assign Project...", lambda: self._assign_project(file_path))
        manual_action = menu.addAction("Add Manual Time...", lambda: self._open_manual_entry(file_path))
        if project_code and self.repository.is_project_locked(project_code):
            manual_action.setEnabled(False)
        menu.addSeparator()
        menu.addAction("Refresh", self._tick)
        menu.exec(self.open_files_table.viewport().mapToGlobal(pos))

    def _show_project_summary_context_menu(self, pos) -> None:
        row = self.project_summary_table.rowAt(pos.y())
        if row < 0:
            return
        project_code = self.project_summary_table.project_code_for_row(row)
        menu = QMenu(self)
        menu.addAction("Generate Project Report", lambda: self._generate_project_report(project_code))
        menu.exec(self.project_summary_table.viewport().mapToGlobal(pos))

    def _export_master_report(self) -> None:
        rows = [
            {
                "project": row["project"],
                "hours": float(row["past_hours"]) + float(row["live_hours"]),
                "amount": float(row["earned"]),
                "trust": 1.0,
            }
            for row in self._last_rows
        ]
        if not rows:
            QMessageBox.information(self, "No data", "No rows available for export.")
            return
        output = self.report_service.create_master_pdf(rows)
        QMessageBox.information(self, "Report created", f"Saved report to:\n{output}")

    def _restore_window_geometry(self) -> None:
        saved = self.settings.value("mainwindow_geometry")
        if saved:
            self.restoreGeometry(saved)
        self._ensure_window_on_screen()

    def _ensure_window_on_screen(self) -> None:
        if self.isMinimized():
            self.showNormal()
        frame = self.frameGeometry()
        visible_area = 0
        for screen in QApplication.screens():
            intersection = frame.intersected(screen.availableGeometry())
            visible_area += intersection.width() * intersection.height()
        min_visible = min(200 * 200, max(1, frame.width() * frame.height()) // 4)
        if visible_area >= min_visible:
            return
        primary = QApplication.primaryScreen()
        if primary:
            geo = primary.availableGeometry()
            self.resize(max(self.width(), 1000), max(self.height(), 680))
            self.move(geo.center().x() - self.width() // 2, geo.center().y() - self.height() // 2)

    def _quit_app(self) -> None:
        self._is_quitting = True
        self.close()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.settings.setValue("mainwindow_geometry", self.saveGeometry())
        self._save_project_overrides()
        if self.minimize_to_tray and not self._is_quitting and self.tray and self.tray.isVisible():
            self.hide()
            self.statusBar().showMessage("VectorTrack is still running in the tray.", 4000)
            event.ignore()
            return
        if self.tray:
            self.tray.hide()
        self.hotkey_service.stop()
        self.tracking_service.stop()
        event.accept()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._ensure_window_on_screen()
        if not ENFORCE_LICENSING:
            self.statusBar().showMessage("Licensing disabled (ENFORCE_LICENSING=False)")
