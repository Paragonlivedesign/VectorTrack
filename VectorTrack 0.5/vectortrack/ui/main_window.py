"""VectorTrack 0.5 main window."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from vectortrack import config
from vectortrack.activity_monitor import ActivityMonitor
from vectortrack.config import format_version
from vectortrack.db.repository import Repository
from vectortrack.models import BillableProject, Client, TimeSession
from vectortrack.process_monitor import ProcessMonitor
from vectortrack.services.backup_service import BackupService
from vectortrack.services.billing_service import BillingContext, BillingService
from vectortrack.services.import_export import ImportExportService
from vectortrack.services.log_service import LogService
from vectortrack.services.report_data import ReportDataBuilder, ReportFilter
from vectortrack.services.report_service import ReportService
from vectortrack.services.autostart import set_enabled as set_autostart_enabled
from vectortrack.services.hotkey_service import HotkeyService
from vectortrack.services.notification_service import NotificationService
from vectortrack.services.project_sync import sync_orphan_project_codes
from vectortrack.services.tracking_service import TrackingService
from vectortrack.ui.clients_tab import ClientsTab
from vectortrack.ui.dashboard_strip import DashboardStrip
from vectortrack.ui.heatmap_widget import HeatmapWidget
from vectortrack.ui.history_browser import HistoryBrowser
from vectortrack.ui.hud_window import HUDWindow
from vectortrack.ui.formatting import project_display_name, resolve_project_code
from vectortrack.ui.open_files_table import OpenFilesTable
from vectortrack.ui.project_summary_table import ProjectSummaryTable
from vectortrack.ui.theme import apply_theme
from vectortrack.ui.app_icon import app_icon
from vectortrack.ui.tray import VectorTrackTray
from vectortrack.ui.dialogs.about_dialog import AboutDialog
from vectortrack.ui.dialogs.backup_restore_dialog import BackupRestoreDialog
from vectortrack.ui.dialogs.bug_report_dialog import BugReportDialog
from vectortrack.ui.dialogs.client_editor_dialog import ClientEditorDialog
from vectortrack.ui.dialogs.donate_dialog import DonateDialog
from vectortrack.ui.dialogs.first_run_wizard import FirstRunWizard
from vectortrack.ui.dialogs.import_bundle_dialog import ImportBundleDialog
from vectortrack.ui.dialogs.log_library_dialog import LogLibraryDialog
from vectortrack.log_parser import expected_log_path_for_exe, vectorworks_log_roaming_dir
from vectortrack.ui.dialogs.vectorworks_log_setup_dialog import VectorworksLogSetupDialog
from vectortrack.ui.dialogs.vectorworks_setup_dialog import VectorworksSetupDialog
from vectortrack.ui.dialogs.manual_entry_dialog import ManualEntryDialog
from vectortrack.ui.dialogs.project_assign_dialog import ProjectAssignDialog
from vectortrack.ui.dialogs.project_editor_dialog import ProjectEditorDialog
from vectortrack.ui.dialogs.new_project_dialog import NewProjectDialog
from vectortrack.ui.dialogs.rate_edit_dialog import RateEditDialog
from vectortrack.ui.dialogs.report_dialog import ReportDialog
from vectortrack.ui.dialogs.settings_dialog import SettingsDialog
from vectortrack.ui.dialogs.update_check_dialog import UpdateCheckDialog
from vectortrack.services.session_aggregator import SessionAggregator
from vectortrack.services.vw_identity import (
    clear_vw_identity_cache,
    resolve_sync_machine_id,
    resolve_sync_machine_label,
    resolve_vw_identity,
)
from vectortrack.ui.dialogs.session_explorer_dialog import SessionExplorerDialog
from vectortrack.sync_config import SyncConfig, default_machine_id, load_sync_config_from_paths_json, settings_keys_from_sync_config, sync_config_to_mapping
from vectortrack.sync_folder import (
    gather_sync_log_paths,
    load_sync_machine_labels,
    merge_remote_assignments,
    push_assignments_snapshot,
    push_log_snapshot,
    resolve_machine_display,
    resolve_sync_folder,
    snapshot_dir,
)


class MainWindow(QMainWindow):
    SUPPORT_EMAIL = "Info@paragonlivedesign.com"
    UNASSIGNED_PROJECT_LABEL = "— Unassigned —"
    _invoke_requested = pyqtSignal(object)

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
        self.report_service = ReportService(output_dir=str(config.reports_dir()))
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
        self.repository.default_hourly_rate = float(self.default_rate)
        self.minimize_to_tray = self.settings.value("minimize_to_tray", True, type=bool)
        self.notifications_enabled = self.settings.value("notifications_enabled", True, type=bool)
        self.global_hotkeys_enabled = self.settings.value("global_hotkeys_enabled", True, type=bool)
        self.eod_notify_enabled = self.settings.value("eod_notify_enabled", True, type=bool)
        self.eod_notify_hour = int(self.settings.value("eod_notify_hour", 17, type=int))
        self.idle_pause_enabled = self.settings.value(
            "idle_pause_enabled", config.DEFAULT_IDLE_PAUSE_ENABLED, type=bool
        )
        self.idle_bypass_mode = self.settings.value(
            "idle_bypass_mode", config.DEFAULT_IDLE_BYPASS_MODE, type=str
        )
        if self.idle_bypass_mode not in config.IDLE_BYPASS_MODES:
            self.idle_bypass_mode = config.DEFAULT_IDLE_BYPASS_MODE
        self.sync_config = self._load_sync_config()
        self.session_aggregator = SessionAggregator(self.repository)
        self.log_cache: dict[str, dict[str, float | datetime]] = {}
        self.file_project_overrides: dict[str, str] = self._load_project_overrides()
        self.merged_assignments: dict[str, str] = {}
        self._assignments_dirty = False
        self._machine_label_cache: dict[str, str] = {}
        self._refresh_merged_assignments()
        self._last_log_sync = datetime.min
        self._last_sync_push = datetime.min
        self._last_sync_push_error = ""
        self._last_rows: list[dict[str, object]] = []
        self._is_quitting = False
        self._known_open_files: set[str] = set()
        self._session_file_order: list[str] = []
        self._budget_notified: dict[str, str] = {}
        self._delta_notified: dict[str, float] = {}
        self._idle_notified = False
        self._eod_notified_date: date | None = None
        self.notification_service = NotificationService(enabled=self.notifications_enabled)
        hotkeys_enabled = self.global_hotkeys_enabled and os.environ.get("VECTORTRACK_TESTING") != "1"
        self.activity_monitor.monitor_keyboard = not hotkeys_enabled
        self.hotkey_service = HotkeyService(
            enabled=hotkeys_enabled,
            dispatch=self._invoke_on_main_thread,
            on_keyboard_activity=self.activity_monitor.bump_activity if hotkeys_enabled else None,
        )
        self._invoke_requested.connect(self._invoke_callback)

        self.setWindowTitle("VectorTrack")
        self.setWindowIcon(app_icon(self))
        self.setMinimumSize(1000, 680)
        self.resize(1320, 820)

        self.tray = VectorTrackTray(self)
        self.tray.show()
        self.notification_service.set_tray(self.tray)
        self.hud = HUDWindow(self)
        self.hud.hide()

        self._build_ui()
        self._create_actions()
        self._build_toolbar()
        self._build_menus()
        self._build_statusbar()
        self._restore_window_geometry()
        self._vw_detect_mode = self._auto_detect_vectorworks()
        self._apply_saved_theme()
        self._write_paths_manifest()

        self.tracking_service.start()
        self._apply_idle_settings()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._tick)
        self.update_timer.start(1000)
        self.history_browser.refresh_requested.connect(self._refresh_history)
        self.open_files_table.assign_project_requested.connect(self._assign_project)
        self.open_files_table.assign_projects_requested.connect(self._assign_projects)
        self.open_files_table.edit_project_requested.connect(self._edit_project_for_file)
        self.open_files_table.manual_entry_requested.connect(self._open_manual_entry)
        self.open_files_table.view_sessions_requested.connect(self._open_session_explorer_for_file)
        self.open_files_table.resume_tracking_requested.connect(self._resume_tracking_for_file)
        self.open_files_table.edit_rate_requested.connect(self._edit_rate_for_file)
        self.project_summary_table.view_sessions_requested.connect(self._open_session_explorer_for_project)
        self.project_summary_table.edit_project_requested.connect(self._show_project_editor)
        self.heatmap_widget.day_clicked.connect(self._jump_history_to_day)
        self.clients_tab.edit_client_requested.connect(self._open_client_editor)
        self.clients_tab.statement_requested.connect(self._generate_client_statement)

        self._setup_hotkeys()
        self._setup_notifications()
        self.hotkey_service.start()

        QTimer.singleShot(50, self._show_first_run_wizard_if_needed)
        QTimer.singleShot(200, self._show_vectorworks_setup_prompts)
        QTimer.singleShot(0, self._tick)
        QTimer.singleShot(150, self._refresh_history)
        QTimer.singleShot(500, lambda: self._maybe_push_log_sync(force=True))

    def _apply_idle_settings(self) -> None:
        self.tracking_service.set_idle_pause_enabled(self.idle_pause_enabled)
        self.tracking_service.set_idle_bypass_mode(self.idle_bypass_mode)
        self.tracking_service.log_open_checker = self._log_file_is_open

    def _log_file_is_open(self, file_path: str) -> bool:
        if not self.import_vw_log_history:
            return False
        _, open_hours = self._log_stats_for_file(file_path, os.path.basename(file_path))
        return open_hours > 0

    def _tracking_status_for_state(self, state) -> str:
        if self.tracking_service.is_paused:
            return "paused"
        if state is not None and self.tracking_service.is_idle_blocked(state.file_path):
            return "idle"
        return "tracking"

    def _tray_status(self, rows: list[dict[str, object]] | None = None) -> str:
        current = self.tracking_service.current_state
        if current is None:
            return "inactive"
        tracking_status = self._tracking_status_for_state(current)
        if tracking_status != "tracking":
            return tracking_status
        source_rows = rows if rows is not None else self._last_rows
        row = next((item for item in source_rows if item.get("file_path") == current.file_path), None)
        row_kind = str(row.get("row_kind", "active")) if row else "active"
        if self._is_live_tracking(current.file_path, row_kind):
            return "tracking"
        return "paused"

    def _update_tray_status(self, rows: list[dict[str, object]] | None = None) -> None:
        status = self._tray_status(rows)
        self.tray.set_tracking_status(status)  # type: ignore[attr-defined]
        self.tray.set_paused(self.tracking_service.is_paused)  # type: ignore[attr-defined]

    def _toggle_pause_from_tray(self) -> None:
        self.pause_action.setChecked(not self.pause_action.isChecked())

    @classmethod
    def create_default(cls) -> "MainWindow":
        settings = QSettings("Paragon", "VectorTrack")
        default_rate = settings.value("default_hourly_rate", 75.0, type=float)
        repository = Repository(default_hourly_rate=float(default_rate))
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
        open_files_header = QHBoxLayout()
        open_files_header.addWidget(QLabel("Open Files"))
        open_files_header.addStretch()
        self.assign_selected_projects_btn = QPushButton("Assign Selected to Project...")
        self.assign_selected_projects_btn.clicked.connect(self._assign_selected_projects)
        open_files_header.addWidget(self.assign_selected_projects_btn)
        top_layout.addLayout(open_files_header)
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
        self._update_pause_action_label()

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
        reports_menu.addAction(
            "Master Report...",
            lambda: self._open_report_dialog(report_type="master"),
        )
        reports_menu.addAction("Generate Selected Project PDF", self._report_selected_project)

        help_menu = self.menuBar().addMenu("Help")
        help_menu.addAction("Report a Bug...", self._show_bug_report_dialog)
        help_menu.addAction("Contact Support", self._contact_support)
        help_menu.addSeparator()
        help_menu.addAction("Check for Updates...", self._check_for_updates)
        help_menu.addAction("About", self._show_about)
        help_menu.addAction("Donate", self._show_donate)

    def _build_statusbar(self) -> None:
        status = QStatusBar(self)
        version_label = QLabel(format_version(include_product_name=False))
        version_label.setObjectName("muted")
        status.addWidget(version_label)
        self.setStatusBar(status)

    def _invoke_callback(self, fn: object) -> None:
        if callable(fn):
            fn()

    def _invoke_on_main_thread(self, fn: Callable[[], None]) -> None:
        self._invoke_requested.emit(fn)

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

    def _load_sync_config(self) -> SyncConfig:
        vw_year = self._current_vw_year()
        if self.settings.contains("sync_enabled"):
            stored_id = str(self.settings.value("sync_machine_id", default_machine_id(), type=str))
            stored_label = str(self.settings.value("sync_machine_label", "", type=str))
            return SyncConfig(
                enabled=self.settings.value("sync_enabled", False, type=bool),
                folder=self.settings.value("sync_folder", "", type=str),
                machine_id=resolve_sync_machine_id(stored_id, vw_year),
                machine_label=resolve_sync_machine_label(stored_label, vw_year),
                sync_on_refresh=self.settings.value("sync_on_refresh", True, type=bool),
            )
        loaded = load_sync_config_from_paths_json(config.paths_json_path())
        return SyncConfig(
            enabled=loaded.enabled,
            folder=loaded.folder,
            machine_id=resolve_sync_machine_id(loaded.machine_id, vw_year),
            machine_label=resolve_sync_machine_label(loaded.machine_label, vw_year),
            sync_on_refresh=loaded.sync_on_refresh,
        )

    def _write_paths_manifest(self) -> None:
        try:
            config.write_paths_json(
                {
                    "vectorworks_path": self.settings.value("vectorworks_path", "", type=str),
                    "vw_log_path": self.vw_log_path,
                    "sync": sync_config_to_mapping(self.sync_config),
                }
            )
        except Exception:
            # Manifest writing is best-effort and should not interrupt UI startup.
            pass

    def _current_vw_year(self) -> int:
        exe = self.process_monitor.vectorworks_path or ""
        match = re.search(r"Vectorworks[\s_]?(\d{4})", exe, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return datetime.now().year

    def _auto_detect_vectorworks(self) -> str:
        """Configure Vectorworks.exe path. Returns saved, auto, or missing."""
        saved = self.settings.value("vectorworks_path", "", type=str)
        if saved and os.path.exists(saved):
            try:
                self.process_monitor.set_vectorworks_path(saved)
                return "saved"
            except Exception:
                pass
        path = self.process_monitor.auto_select_vectorworks()
        if path:
            self.settings.setValue("vectorworks_path", path)
            self._write_paths_manifest()
            return "auto"
        return "missing"

    def _show_vectorworks_setup_prompts(self) -> None:
        if not self.process_monitor.vectorworks_path:
            if self.settings.value("vw_exe_prompt_skipped", False, type=bool):
                self.statusBar().showMessage(
                    "Vectorworks executable not set — use File → Select Vectorworks EXE…",
                    15000,
                )
                return
            dialog = VectorworksSetupDialog(
                browse_directory=self.process_monitor.suggested_exe_browse_directory(),
                parent=self,
            )
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_path:
                try:
                    self.process_monitor.set_vectorworks_path(dialog.selected_path)
                    self.settings.setValue("vectorworks_path", dialog.selected_path)
                    self.settings.setValue("vw_exe_prompt_skipped", False)
                    self.settings.setValue("vw_auto_detect_notified", True)
                    self._write_paths_manifest()
                    self._tick()
                    self._show_log_setup_prompt_if_needed()
                except Exception as exc:
                    QMessageBox.warning(self, "Vectorworks path error", str(exc))
            else:
                self.settings.setValue("vw_exe_prompt_skipped", True)
                self.statusBar().showMessage(
                    "Vectorworks executable not set — use File → Select Vectorworks EXE…",
                    15000,
                )
            return

        self._show_log_setup_prompt_if_needed()

        if (
            self._vw_detect_mode == "auto"
            and not self.settings.value("vw_auto_detect_notified", False, type=bool)
        ):
            exe_path = self.process_monitor.vectorworks_path or ""
            version_label = os.path.basename(os.path.dirname(exe_path)) or "Vectorworks"
            self.notification_service.notify(
                "Vectorworks linked",
                f"Using {version_label} at {exe_path}. Change via File → Select Vectorworks EXE…",
            )
            self.settings.setValue("vw_auto_detect_notified", True)

    def _show_log_setup_prompt_if_needed(self) -> None:
        if not self.import_vw_log_history:
            return
        if not self.process_monitor.vectorworks_path:
            return
        if self._local_log_paths():
            self.settings.setValue("vw_log_setup_notified", True)
            return
        if self.settings.value("vw_log_prompt_skipped", False, type=bool):
            self.statusBar().showMessage(
                "Vectorworks Log.txt not found — use Edit → Log Library… or enable "
                "Log time in program under Vectorworks Preferences → Session.",
                15000,
            )
            return

        exe_path = self.process_monitor.vectorworks_path or ""
        expected = expected_log_path_for_exe(exe_path) or ""
        dialog = VectorworksLogSetupDialog(
            expected_log_path=expected,
            browse_directory=vectorworks_log_roaming_dir(),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_path:
            self.vw_log_path = dialog.selected_path
            self.settings.setValue("vw_log_path", dialog.selected_path)
            self.settings.setValue("vw_log_prompt_skipped", False)
            self.settings.setValue("vw_log_setup_notified", True)
            self._write_paths_manifest()
            self._tick()
            return

        self.settings.setValue("vw_log_prompt_skipped", True)
        self.statusBar().showMessage(
            "Vectorworks Log.txt not found — enable Log time in program under "
            "Vectorworks Preferences → Session, then use Edit → Log Library…",
            15000,
        )

    def _select_vectorworks_exe(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Vectorworks executable",
            self.process_monitor.suggested_exe_browse_directory(),
            "Executable (*.exe);;All files (*)",
        )
        if not file_path:
            return
        try:
            self.process_monitor.set_vectorworks_path(file_path)
            self.settings.setValue("vectorworks_path", file_path)
            self.settings.setValue("vw_exe_prompt_skipped", False)
            self.settings.setValue("vw_auto_detect_notified", True)
            self._write_paths_manifest()
            self._tick()
            self._show_log_setup_prompt_if_needed()
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
        self._assignments_dirty = True

    def _refresh_merged_assignments(self) -> None:
        sync_folder = resolve_sync_folder(self.sync_config)
        vw_year = self._current_vw_year()
        if sync_folder and self.sync_config.enabled:
            self.merged_assignments = merge_remote_assignments(
                sync_folder,
                vw_year,
                self.file_project_overrides,
                local_machine_id=self.sync_config.machine_id,
            )
            self._machine_label_cache = load_sync_machine_labels(sync_folder, vw_year)
        else:
            self.merged_assignments = {
                os.path.basename(str(path).replace("\\", "/")): str(code).strip()
                for path, code in self.file_project_overrides.items()
                if path and code
            }
            self._machine_label_cache = {}
        self._sync_orphan_project_assignments()

    def _effective_assigned_files(self) -> dict[str, str]:
        assigned = dict(self.merged_assignments)
        for file_path, code in self.file_project_overrides.items():
            if file_path and code:
                assigned[os.path.basename(str(file_path).replace("\\", "/"))] = str(code).strip()
        return assigned

    def _maybe_push_assignments(self, *, force: bool = False) -> None:
        if not self.sync_config.enabled or not self.sync_config.folder.strip():
            return
        if not force and not self._assignments_dirty:
            return
        ok, _err = push_assignments_snapshot(
            self.file_project_overrides,
            self.sync_config,
            self._current_vw_year(),
        )
        if ok:
            self._assignments_dirty = False

    def _machine_display(self, machine_id: str) -> str:
        sync_folder = resolve_sync_folder(self.sync_config)
        return resolve_machine_display(
            machine_id,
            sync_folder=sync_folder,
            vw_year=self._current_vw_year(),
            local_config=self.sync_config,
            label_cache=self._machine_label_cache,
        )

    def _history_rows_from_db(self, selected_project: str, start_limit: datetime, end_limit: datetime) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        sessions = self.repository.list_sessions(project_id=selected_project or None, include_open=True, limit=5000)
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
                    "machine": self._machine_display(session.machine_id or ""),
                    "hours": session.active_duration.total_seconds() / 3600.0,
                    "rate": session.hourly_rate,
                    "amount": session.billable_amount,
                    "status": "Open" if session.end_time is None else "Closed",
                }
            )
        return rows

    def _merged_report_rows(
        self,
        *,
        start_limit: datetime,
        end_limit: datetime,
        project_code: str = "",
    ):
        dataset = self._report_data_builder().build(
            ReportFilter(
                from_dt=start_limit,
                to_dt=end_limit,
                project_code=project_code,
            )
        )
        return sorted(dataset.rows, key=lambda row: row.start, reverse=True)

    def _history_rows_from_merged(
        self,
        selected_project: str,
        start_limit: datetime,
        end_limit: datetime,
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for report_row in self._merged_report_rows(
            start_limit=start_limit,
            end_limit=end_limit,
            project_code=selected_project,
        ):
            project_label = report_row.project_label or report_row.project_code
            if report_row.is_locked:
                project_label = f"{project_label} [LOCKED]"
            rows.append(
                {
                    "start": report_row.start.strftime("%Y-%m-%d %H:%M"),
                    "end": report_row.end.strftime("%Y-%m-%d %H:%M") if report_row.end else "Open",
                    "project": project_label,
                    "file": report_row.file,
                    "machine": self._machine_display(report_row.machine_id),
                    "hours": report_row.raw_hours,
                    "rate": report_row.rate,
                    "amount": report_row.raw_amount,
                    "status": report_row.status,
                }
            )
        return rows

    def _cleanup_stale_project_overrides(self) -> None:
        stale_paths = [
            path
            for path, code in self.file_project_overrides.items()
            if code and self.repository.get_project_by_code(str(code).strip()) is None
        ]
        if not stale_paths:
            return
        for path in stale_paths:
            del self.file_project_overrides[path]
        self._save_project_overrides()

    def _sync_orphan_project_assignments(self) -> None:
        self._cleanup_stale_project_overrides()
        codes: set[str] = set()
        for code in self.file_project_overrides.values():
            if code:
                codes.add(str(code).strip())
        for session in self.repository.list_sessions(include_open=True, limit=15000):
            if session.project_id:
                codes.add(str(session.project_id).strip())
        created = sync_orphan_project_codes(
            self.repository,
            codes,
            default_rate=float(self.default_rate),
        )
        if created:
            names = ", ".join(created[:3])
            suffix = f" (+{len(created) - 3} more)" if len(created) > 3 else ""
            self.statusBar().showMessage(
                f"Registered project(s) in Project Editor: {names}{suffix}",
                5000,
            )

    def _local_log_paths(self) -> list[str]:
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

    def _maybe_push_log_sync(self, *, force: bool = False) -> bool:
        """Push local Vectorworks Log.txt to the cross-machine sync folder."""
        if not self.sync_config.enabled or not self.sync_config.sync_on_refresh:
            return False
        if not self.sync_config.folder.strip():
            self._last_sync_push_error = "Sync folder is not set"
            return False
        if not force and (datetime.now() - self._last_sync_push).total_seconds() < 60:
            return False

        paths = self._local_log_paths()
        if not paths:
            self._last_sync_push_error = "Vectorworks Log.txt not found on this machine"
            return False

        ok, err = push_log_snapshot(
            paths[0],
            self.sync_config,
            self._current_vw_year(),
        )
        if ok:
            self._last_sync_push = datetime.now()
            self._last_sync_push_error = ""
            dest = snapshot_dir(
                self.sync_config.folder.strip(),
                self.sync_config.machine_id,
                self._current_vw_year(),
            )
            self.statusBar().showMessage(f"Log sync updated: {dest}", 4000)
            return True

        self._last_sync_push_error = err or "Unknown sync error"
        self.statusBar().showMessage(f"Log sync failed: {self._last_sync_push_error}", 8000)
        return False

    def _active_log_paths(self) -> list[str]:
        paths = self._local_log_paths()
        if self.sync_config.enabled and paths:
            self._maybe_push_log_sync()
            paths, _machine_count = gather_sync_log_paths(
                paths,
                self.sync_config,
                self._current_vw_year(),
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

    def _project_for_file(self, file_path: str, state=None) -> str:
        override = self.file_project_overrides.get(file_path)
        if override:
            return override
        basename = os.path.basename(str(file_path).replace("\\", "/"))
        merged = self.merged_assignments.get(basename, "")
        if merged:
            return merged
        if state is not None and state.project_id:
            if self.repository.get_project_by_code(state.project_id):
                return state.project_id
        return ""

    def _project_display(self, project_code: str) -> str:
        if not project_code:
            return self.UNASSIGNED_PROJECT_LABEL
        project = self.repository.get_project_by_code(project_code)
        if project is not None:
            return project_display_name(project.name, project.project_code)
        return project_code

    def _project_options(self) -> list[tuple[str, str]]:
        return [(code, label) for code, label, _rate in self._project_options_with_rates()]

    def _project_options_with_rates(self) -> list[tuple[str, str, float]]:
        options: list[tuple[str, str, float]] = []
        for project in self.repository.list_projects():
            label = project_display_name(project.name, project.project_code)
            options.append((project.project_code, label, float(project.hourly_rate)))
        return sorted(options, key=lambda item: item[1].lower())

    def _rate_for_project(self, project_code: str) -> float:
        return self.repository.resolve_hourly_rate(project_code)

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
        if not self.idle_pause_enabled:
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
            project = str(row.get("project_code") or row.get("project") or "")
            if not project or project == self.UNASSIGNED_PROJECT_LABEL:
                continue
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

    def _update_session_files(self, open_paths: set[str], closed_paths: list[str]) -> None:
        for file_path in closed_paths:
            if file_path and file_path not in self._session_file_order:
                self._session_file_order.append(file_path)
        for file_path in open_paths:
            if not file_path:
                continue
            if file_path not in self._session_file_order:
                self._session_file_order.append(file_path)

    def _ordered_session_paths(self, open_paths: set[str], active_path: str | None) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()

        def add_path(path: str | None) -> None:
            if not path or path in seen:
                return
            seen.add(path)
            ordered.append(path)

        add_path(active_path)
        for path in self._session_file_order:
            if path in open_paths and path != active_path:
                add_path(path)
        for path in reversed(self._session_file_order):
            if path not in open_paths:
                add_path(path)
        return ordered

    def _tracked_file_path(self) -> str:
        current = self.tracking_service.current_state
        return current.file_path if current else ""

    def _status_for_row(self, file_path: str, row_kind: str) -> str:
        is_tracked = self._tracked_file_path() == file_path
        if row_kind == "active":
            if is_tracked:
                if self.tracking_service.is_paused:
                    return "Active (Paused)"
                if self.tracking_service.is_idle_blocked(file_path):
                    return "Active (Idle)"
            return "Active"
        if row_kind == "open":
            if is_tracked:
                if self.tracking_service.is_paused:
                    return "Paused"
                if self.tracking_service.is_idle_blocked(file_path):
                    return "Open (Idle)"
            return "Open"
        return "Recent"

    def _row_for_file(
        self,
        file_path: str,
        *,
        row_kind: str,
        is_open: bool,
    ) -> dict[str, object]:
        state = self.tracking_service.states_by_file.get(file_path)
        project_code = self._project_for_file(file_path, state)
        open_session = self.repository.get_open_live_session(file_path) if is_open else None
        if open_session is not None:
            rate = float(open_session.hourly_rate)
        else:
            rate = self._rate_for_project(project_code)
        live_hours = float(state.tracked_hours if state and is_open else 0.0)
        closed_hours, open_hours = self._log_stats_for_file(file_path, Path(file_path).name)
        delta_hours = (open_hours - live_hours) if is_open else 0.0
        billing = self.billing_service.compute(
            BillingContext(
                rate=rate,
                duration_hours=max(0.0, closed_hours + (live_hours if is_open else 0.0)),
                started_at=(state.started_at if state and is_open else None),
            )
        )
        if row_kind == "active":
            status = self._status_for_row(file_path, row_kind)
        elif is_open:
            status = self._status_for_row(file_path, "open")
        else:
            status = "Recent"
        is_tracking = self._is_live_tracking(file_path, row_kind)
        return {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "project": self._project_display(project_code),
            "project_code": project_code,
            "status": status,
            "past_hours": closed_hours,
            "live_hours": live_hours,
            "delta_hours": delta_hours,
            "rate": rate,
            "earned": billing.total_due,
            "row_kind": row_kind,
            "is_tracking": is_tracking,
        }

    def _is_live_tracking(self, file_path: str, row_kind: str) -> bool:
        current = self.tracking_service.current_state
        if current is None or current.file_path != file_path:
            return False
        if row_kind not in ("active", "open"):
            return False
        if self.tracking_service.meeting_topic or current.meeting_mode:
            return True
        return self.tracking_service.should_count_time(file_path)

    def _rows_from_tracking(self) -> list[dict[str, object]]:
        windows = self.process_monitor.vectorworks_windows
        open_paths = {window.file_path for window in windows if window.file_path}
        closed_paths = self.process_monitor.get_closed_files()
        self._update_session_files(open_paths, closed_paths)

        active_path = self.process_monitor.get_foreground_file()
        if not active_path and self.tracking_service.current_state:
            active_path = self.tracking_service.current_state.file_path

        rows: list[dict[str, object]] = []
        for file_path in self._ordered_session_paths(open_paths, active_path):
            is_open = file_path in open_paths
            if file_path == active_path and is_open:
                row_kind = "active"
            elif is_open:
                row_kind = "open"
            else:
                row_kind = "recent"
            rows.append(
                self._row_for_file(
                    file_path,
                    row_kind=row_kind,
                    is_open=is_open,
                )
            )
        return rows

    def _sync_project_overrides_to_tracking(self) -> None:
        for file_path, project_code in self.file_project_overrides.items():
            state = self.tracking_service.states_by_file.get(file_path)
            if state is None or state.project_id == project_code:
                continue
            state.project_id = project_code
            self.repository.update_session_duration(state, 0.0)

    def _tick(self) -> None:
        if not self.process_monitor.vectorworks_path:
            self.statusBar().showMessage("Vectorworks executable not set")
            return
        self.tracking_service.tick()
        self._sync_project_overrides_to_tracking()
        rows = self._rows_from_tracking()
        self._last_rows = rows
        self.open_files_table.update_rows(rows)
        self._refresh_project_summary()
        self._refresh_dash_metrics(rows)
        self._refresh_hud(rows)
        self._update_tray_status(rows)
        self._check_workflow_notifications(rows)
        if (datetime.now() - self._last_log_sync) > timedelta(seconds=60):
            self._last_log_sync = datetime.now()
            self._refresh_history()
        self._maybe_push_log_sync()

    def _refresh_project_summary(self) -> None:
        if self.import_vw_log_history:
            start = datetime(1970, 1, 1)
            end = datetime(9999, 12, 31, 23, 59, 59)
            per_project: dict[str, dict[str, float]] = {}
            for project in self.repository.list_projects():
                per_project[project.project_code] = {
                    "tracked_hours": 0.0,
                    "billable": 0.0,
                    "rate": float(project.hourly_rate),
                }
            for report_row in self._merged_report_rows(start_limit=start, end_limit=end):
                if report_row.excluded:
                    continue
                code = report_row.project_code
                if not code:
                    continue
                agg = per_project.setdefault(
                    code,
                    {
                        "tracked_hours": 0.0,
                        "billable": 0.0,
                        "rate": float(report_row.rate),
                    },
                )
                agg["tracked_hours"] += report_row.raw_hours
                agg["billable"] += report_row.raw_amount
        else:
            per_project = {}
            for project in self.repository.list_projects():
                per_project[project.project_code] = {
                    "tracked_hours": 0.0,
                    "billable": 0.0,
                    "rate": float(project.hourly_rate),
                }
            for session in self.repository.list_sessions(include_open=True, limit=15000):
                project = session.project_id
                if not project:
                    continue
                agg = per_project.setdefault(
                    project,
                    {
                        "tracked_hours": 0.0,
                        "billable": 0.0,
                        "rate": float(session.hourly_rate),
                    },
                )
                agg["tracked_hours"] += session.active_duration.total_seconds() / 3600.0
                agg["billable"] += session.billable_amount
        self.project_summary_table.set_rows(
            [
                {
                    "project": self._project_display(key),
                    "project_code": key,
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
        active_row = next((row for row in rows if row.get("row_kind") == "active"), None)
        active_project = None
        if active_row:
            active_project = self._project_display(
                str(active_row.get("project_code") or active_row.get("project") or "")
            )
        active_live = float(active_row["live_hours"]) if active_row else 0.0
        active_tracking = bool(active_row.get("is_tracking")) if active_row else False
        self.dashboard_strip.set_metrics(
            today_hours=today_hours,
            week_hours=week_hours,
            month_hours=max(month_hours, total_hours),
            earned=total_earned,
            active_project=active_project,
            active_live_hours=active_live,
            active_is_tracking=active_tracking,
        )

    def _refresh_hud(self, rows: list[dict[str, object]]) -> None:
        current = self.tracking_service.current_state
        if not current:
            self.hud.set_stats("No active file", 0.0, 0.0)
            return
        row = next((item for item in rows if item["file_path"] == current.file_path), None)
        earned = float(row["earned"]) if row else 0.0
        row_kind = str(row.get("row_kind", "")) if row else ""
        is_tracking = bool(row.get("is_tracking")) if row else False
        if not is_tracking:
            is_tracking = self._is_live_tracking(current.file_path, str(row.get("row_kind", "")) if row else "active")
        tracking_status = self._tracking_status_for_state(current)
        project_name = str(row.get("project_code") or row.get("project") or current.project_id) if row else current.project_id
        self.hud.set_stats(
            os.path.basename(current.file_path),
            float(current.tracked_hours),
            earned,
            is_tracking=is_tracking,
            tracking_status=tracking_status,
            project_name=project_name,
        )

    def _refresh_history(self) -> None:
        self._maybe_push_assignments()
        self._refresh_merged_assignments()
        selected_project = self.history_browser.selected_project()
        start_limit = self.history_browser.from_filter.dateTime().toPyDateTime()
        end_limit = self.history_browser.to_filter.dateTime().toPyDateTime()
        if self.import_vw_log_history:
            rows = self._history_rows_from_merged(selected_project, start_limit, end_limit)
        else:
            rows = self._history_rows_from_db(selected_project, start_limit, end_limit)
        self.history_browser.set_rows(rows)
        self.history_browser.set_project_options([project.project_code for project in self.repository.list_projects()])
        self._refresh_heatmap()
        self._refresh_project_summary()
        self.clients_tab.refresh()

    def _refresh_heatmap(self) -> None:
        totals: dict[date, float] = {}
        if self.import_vw_log_history:
            start = datetime(1970, 1, 1)
            end = datetime(9999, 12, 31, 23, 59, 59)
            for report_row in self._merged_report_rows(start_limit=start, end_limit=end):
                if report_row.excluded:
                    continue
                day = report_row.start.date()
                totals[day] = totals.get(day, 0.0) + report_row.raw_hours
        else:
            sessions = self.repository.list_sessions(include_open=True, limit=15000)
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
        if not file_path:
            return
        self._assign_projects([file_path])

    def _assign_selected_projects(self) -> None:
        file_paths = self.open_files_table.selected_file_paths()
        if not file_paths:
            QMessageBox.information(
                self,
                "No selection",
                "Select one or more files in the Open Files list first.",
            )
            return
        self._assign_projects(file_paths)

    def _assign_projects(self, file_paths: list[str]) -> None:
        paths = [path for path in file_paths if path]
        if not paths:
            return
        self._sync_orphan_project_assignments()
        projects = self._project_options()
        if not projects:
            QMessageBox.information(self, "No projects", "Create a project first in Project Editor.")
            return
        dialog = ProjectAssignDialog(file_paths=paths, projects=projects, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        project_code = dialog.selected_project()
        if not project_code:
            return
        rate_strategy = dialog.selected_rate_strategy()
        for file_path in dialog.file_paths:
            self.file_project_overrides[file_path] = project_code
            _open_session, split = self.repository.assign_file_to_project(
                file_path,
                project_code,
                rate_strategy=rate_strategy,
            )
            state = self.tracking_service.states_by_file.get(file_path)
            if state is not None:
                state.project_id = project_code
                if split:
                    now = datetime.now()
                    state.tracked_seconds = 0.0
                    state.started_at = now
                    state.last_tick_at = now
                self.repository.update_session_duration(state, 0.0)
        self._save_project_overrides()
        self._refresh_merged_assignments()
        self._maybe_push_assignments(force=True)
        self._sync_orphan_project_assignments()
        self._tick()

    def _edit_rate_for_file(self, file_path: str) -> None:
        if not file_path:
            return
        state = self.tracking_service.states_by_file.get(file_path)
        project_code = self._project_for_file(file_path, state)
        open_session = self.repository.get_open_live_session(file_path)
        current_rate = (
            float(open_session.hourly_rate)
            if open_session is not None
            else self._rate_for_project(project_code)
        )
        dialog = RateEditDialog(current_rate=current_rate, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        new_rate = dialog.hourly_rate()
        updated = self.repository.set_open_session_rate(file_path, new_rate)
        if updated is None and state is not None:
            session = TimeSession(
                project_id=state.project_id,
                file_path=file_path,
                start_time=state.started_at,
                hourly_rate=new_rate,
                rate_overridden=True,
                live_duration=timedelta(seconds=max(0.0, state.tracked_seconds)),
                source="live",
            )
            self.repository.upsert_open_session(session)
        elif state is not None:
            self.repository.update_session_duration(state, 0.0)
        self._tick()
        self._refresh_history()

    def _edit_project_for_file(self, file_path: str) -> None:
        if not file_path:
            return
        state = self.tracking_service.states_by_file.get(file_path)
        project_code = self._project_for_file(file_path, state)
        if not project_code:
            self._assign_project(file_path)
            return
        self._sync_orphan_project_assignments()
        self._show_project_editor(project_code)

    def _open_manual_entry(self, suggested_file: str) -> None:
        projects = self._project_options_with_rates()
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
            rate_overridden=True,
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
        self.repository.default_hourly_rate = self.default_rate
        self.minimize_to_tray = bool(values["minimize_to_tray"])
        self.notifications_enabled = bool(values.get("notifications_enabled", True))
        self.global_hotkeys_enabled = bool(values.get("global_hotkeys_enabled", True))
        self.eod_notify_enabled = bool(values.get("eod_notify_enabled", True))
        self.eod_notify_hour = int(values.get("eod_notify_hour", 17))
        self.idle_pause_enabled = bool(values.get("idle_pause_enabled", config.DEFAULT_IDLE_PAUSE_ENABLED))
        self.idle_bypass_mode = str(values.get("idle_bypass_mode", config.DEFAULT_IDLE_BYPASS_MODE))
        if self.idle_bypass_mode not in config.IDLE_BYPASS_MODES:
            self.idle_bypass_mode = config.DEFAULT_IDLE_BYPASS_MODE
        self.sync_config = SyncConfig(
            enabled=bool(values.get("sync_enabled", False)),
            folder=str(values.get("sync_folder", "")),
            machine_id=resolve_sync_machine_id(str(values.get("sync_machine_id", "")), self._current_vw_year()),
            machine_label=resolve_sync_machine_label(
                str(values.get("sync_machine_label", "")),
                self._current_vw_year(),
            ),
            sync_on_refresh=bool(values.get("sync_on_refresh", True)),
        )
        clear_vw_identity_cache()
        self._refresh_merged_assignments()
        for key, value in settings_keys_from_sync_config(self.sync_config).items():
            self.settings.setValue(key, value)
        self.log_cache.clear()
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
        self._apply_idle_settings()
        self._apply_saved_theme()
        self._write_paths_manifest()
        if self.sync_config.enabled:
            if not self.sync_config.folder.strip():
                QMessageBox.warning(
                    self,
                    "Log sync",
                    "Cross-machine log sync is enabled but no sync folder is set.",
                )
            elif not self._maybe_push_log_sync(force=True):
                detail = self._last_sync_push_error or "Check that Vectorworks Log.txt is linked."
                dest = snapshot_dir(
                    self.sync_config.folder.strip(),
                    self.sync_config.machine_id,
                    self._current_vw_year(),
                )
                QMessageBox.warning(
                    self,
                    "Log sync",
                    f"Could not write log snapshot.\n\n{detail}\n\nExpected folder:\n{dest}",
                )
            else:
                dest = snapshot_dir(
                    self.sync_config.folder.strip(),
                    self.sync_config.machine_id,
                    self._current_vw_year(),
                )
                QMessageBox.information(
                    self,
                    "Log sync",
                    f"Log snapshot saved.\n\n{dest}",
                )
            self._maybe_push_assignments(force=True)
        self._tick()

    def _show_project_editor(self, project_code: str | None = None) -> None:
        code = (project_code or "").strip()
        if code:
            self._sync_orphan_project_assignments()
        ProjectEditorDialog(
            self.repository,
            self,
            initial_project_code=code or None,
        ).exec()
        self._sync_orphan_project_assignments()
        self._tick()
        self._refresh_history()

    def _create_new_project(self) -> None:
        dialog = NewProjectDialog(default_rate=self.default_rate, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        values = dialog.values()
        code = str(values["project_code"]).strip()
        name = str(values["project_name"]).strip()
        client_name = str(values["client_name"]).strip() or "Default"
        resolved_code = resolve_project_code(name, code)
        if not resolved_code:
            QMessageBox.warning(self, "Missing values", "Project name is required.")
            return
        existing = self.repository.get_project_by_code(resolved_code)
        if existing is not None:
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
                hourly_rate=float(values["hourly_rate"]),
            )
        )
        self._tick()
        self._refresh_history()
        self.statusBar().showMessage(f"Created project {name}", 3000)

    def _show_about(self) -> None:
        AboutDialog(self).exec()

    def _check_for_updates(self) -> None:
        UpdateCheckDialog(self).exec()

    def _show_donate(self) -> None:
        DonateDialog(self).exec()

    def _open_client_editor(self, client_id: int | None) -> None:
        dialog = ClientEditorDialog(self.repository, client_id=client_id, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.clients_tab.refresh()

    def _report_data_builder(self) -> ReportDataBuilder:
        return ReportDataBuilder(
            repository=self.repository,
            session_aggregator=self.session_aggregator,
            billing_service=self.billing_service,
            log_service=self.log_service,
            log_paths=self._active_log_paths(),
            assigned_files=self._effective_assigned_files(),
        )

    def _generate_client_statement(self, client_id: int) -> None:
        self._open_report_dialog(report_type="client", client_id=client_id)

    def _open_log_library_dialog(self) -> None:
        paths, description = self.log_service.resolve_sources(
            vw_exe_path=self.process_monitor.vectorworks_path,
            manual_log_path=self.vw_log_path or None,
            merge_other_years=self.vw_log_merge_years,
        )
        LogLibraryDialog(
            self.repository,
            linked_log_paths=paths,
            linked_log_description=description,
            parent=self,
        ).exec()
        self.log_cache.clear()
        self._tick()

    def _open_import_bundle_dialog(self) -> None:
        dialog = ImportBundleDialog(self.repository, self.import_export_service, self)
        dialog.imported.connect(lambda _count: self._refresh_history())
        dialog.exec()

    def _open_backup_restore_dialog(self) -> None:
        BackupRestoreDialog(self.backup_service, self).exec()

    def _open_report_dialog(
        self,
        report_type: str = "master",
        project_code: str = "",
        client_id: int = 0,
    ) -> None:
        ReportDialog(
            repository=self.repository,
            report_service=self.report_service,
            billing_service=self.billing_service,
            session_aggregator=self.session_aggregator,
            log_service=self.log_service,
            log_paths=self._active_log_paths(),
            assigned_files=self._effective_assigned_files(),
            initial_report_type=report_type,
            initial_project_code=project_code,
            initial_client_id=client_id,
            parent=self,
        ).exec()

    def _show_bug_report_dialog(self) -> None:
        BugReportDialog(self).exec()

    def _contact_support(self) -> None:
        QDesktopServices.openUrl(QUrl(f"mailto:{self.SUPPORT_EMAIL}"))

    def _update_pause_action_label(self) -> None:
        paused = self.tracking_service.is_paused
        self.pause_action.blockSignals(True)
        self.pause_action.setChecked(paused)
        self.pause_action.blockSignals(False)
        self.pause_action.setText("Resume Tracking" if paused else "Pause Tracking")
        self.tray.set_paused(paused)  # type: ignore[attr-defined]
        self._update_tray_status()

    def _clear_tracking_blocks(self) -> None:
        self.activity_monitor.bump_activity()
        self._idle_notified = False

    def _resume_tracking_for_file(self, file_path: str) -> None:
        if not file_path:
            return
        if self.tracking_service.is_paused:
            self.pause_action.setChecked(False)
            return
        self._clear_tracking_blocks()
        self.statusBar().showMessage("Tracking resumed", 2500)
        self._tick()

    def _set_pause_state(self, paused: bool) -> None:
        self.tracking_service.set_paused(paused)
        if not paused:
            self._clear_tracking_blocks()
        self._update_pause_action_label()
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
        self._open_report_dialog(report_type="project", project_code=project_code)

    def _open_session_explorer_for_file(self, file_path: str) -> None:
        if not file_path:
            return
        state = self.tracking_service.states_by_file.get(file_path)
        project_code = self._project_for_file(file_path, state)
        log_paths = self._active_log_paths()

        def reload() -> list:
            return self.session_aggregator.sessions_for_file(
                file_path=file_path,
                log_paths=log_paths,
                project_id=project_code or None,
            )

        dialog = SessionExplorerDialog(
            repository=self.repository,
            log_paths=log_paths,
            mode="file",
            target=file_path,
            project_id=project_code,
            reload_callback=reload,
            report_service=self.report_service,
            data_builder=self._report_data_builder(),
            machine_display=self._machine_display,
            parent=self,
        )
        dialog.exec()
        self._tick()
        self._refresh_history()

    def _open_session_explorer_for_project(self, project_code: str) -> None:
        if not project_code:
            return
        log_paths = self._active_log_paths()

        def reload() -> list:
            return self.session_aggregator.sessions_for_project(
                project_code=project_code,
                log_paths=log_paths,
                assigned_files=self._effective_assigned_files(),
            )

        dialog = SessionExplorerDialog(
            repository=self.repository,
            log_paths=log_paths,
            mode="project",
            target=project_code,
            project_id=project_code,
            reload_callback=reload,
            report_service=self.report_service,
            data_builder=self._report_data_builder(),
            machine_display=self._machine_display,
            parent=self,
        )
        dialog.exec()
        self._tick()
        self._refresh_history()

    def _show_open_files_context_menu(self, pos) -> None:
        selected_paths = self.open_files_table.selected_file_paths()
        row = self.open_files_table.rowAt(pos.y())
        if row < 0 and not selected_paths:
            return
        file_path = self.open_files_table.file_path_for_row(row) if row >= 0 else ""
        if file_path and file_path not in selected_paths:
            selected_paths = [file_path]
        project_code = self.open_files_table.project_code_for_row(row) if row >= 0 else ""
        menu = QMenu(self)
        if len(selected_paths) > 1:
            menu.addAction(
                "Assign Selected to Project...",
                lambda: self._assign_projects(selected_paths),
            )
        else:
            menu.addAction("Assign Project...", lambda: self._assign_project(selected_paths[0]))
        if len(selected_paths) == 1:
            if project_code:
                menu.addAction(
                    "Edit Project...",
                    lambda: self._show_project_editor(project_code),
                )
            menu.addAction(
                "View Sessions...",
                lambda: self._open_session_explorer_for_file(selected_paths[0]),
            )
            manual_action = menu.addAction(
                "Add Manual Time...",
                lambda: self._open_manual_entry(selected_paths[0]),
            )
            if project_code and self.repository.is_project_locked(project_code):
                manual_action.setEnabled(False)
        menu.addSeparator()
        menu.addAction("Refresh", self._tick)
        menu.exec(self.open_files_table.viewport().mapToGlobal(pos))

    def _show_project_summary_context_menu(self, pos) -> None:
        row = self.project_summary_table.rowAt(pos.y())
        menu = QMenu(self)
        if row < 0:
            menu.addAction("New Project...", self._create_new_project)
            menu.addAction("Project Editor...", self._show_project_editor)
            menu.addSeparator()
            menu.addAction("Refresh", self._tick)
            menu.exec(self.project_summary_table.viewport().mapToGlobal(pos))
            return
        project_code = self.project_summary_table.project_code_for_row(row)
        menu.addAction("New Project...", self._create_new_project)
        menu.addSeparator()
        menu.addAction("Edit Project...", lambda: self._show_project_editor(project_code))
        menu.addAction("View Sessions...", lambda: self._open_session_explorer_for_project(project_code))
        menu.addAction("Generate Project Report", lambda: self._open_report_dialog(report_type="project", project_code=project_code))
        menu.addAction(
            "Project Editor...",
            lambda: self._show_project_editor(project_code),
        )
        menu.exec(self.project_summary_table.viewport().mapToGlobal(pos))

    def _restore_window_geometry(self) -> None:
        saved = self.settings.value("mainwindow_geometry")
        if saved:
            self.restoreGeometry(saved)
        self._ensure_window_on_screen()

    def _ensure_window_on_screen(self) -> None:
        if not self.isVisible():
            return
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
