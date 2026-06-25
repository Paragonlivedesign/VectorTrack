"""Global settings dialog for VectorTrack."""

from __future__ import annotations

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from vectortrack.config import (
    DEFAULT_HOURLY_RATE,
    DEFAULT_IDLE_BYPASS_MODE,
    DEFAULT_IDLE_MINUTES,
    DEFAULT_IDLE_PAUSE_ENABLED,
    ENFORCE_LICENSING,
    IDLE_BYPASS_MODES,
    IDLE_TIMEOUT_HELPER_TEXT,
    SHOW_PORTABLE_MODE_UI,
)
from vectortrack.services.autostart import is_enabled as autostart_is_enabled
from vectortrack.services.vw_identity import (
    resolve_sync_machine_id,
    resolve_sync_machine_label,
    resolve_vw_identity,
)
from vectortrack.sync_config import default_machine_id


class SettingsDialog(QDialog):
    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.default_rate = QDoubleSpinBox()
        self.default_rate.setRange(0, 10000)
        self.default_rate.setDecimals(2)
        self.default_rate.setValue(settings.value("default_hourly_rate", DEFAULT_HOURLY_RATE, type=float))
        form.addRow("Default hourly rate", self.default_rate)

        form.addRow("", QLabel("Idle detection"))
        self.idle_pause_enabled = QCheckBox("Pause tracking when idle")
        self.idle_pause_enabled.setChecked(
            settings.value("idle_pause_enabled", DEFAULT_IDLE_PAUSE_ENABLED, type=bool)
        )
        self.idle_pause_enabled.toggled.connect(self._sync_idle_controls)
        form.addRow("", self.idle_pause_enabled)

        self.idle_minutes = QSpinBox()
        self.idle_minutes.setRange(1, 240)
        self.idle_minutes.setValue(settings.value("default_idle_timeout", DEFAULT_IDLE_MINUTES, type=int))
        form.addRow("Idle timeout (minutes)", self.idle_minutes)

        self.idle_bypass_mode = QComboBox()
        for mode, label in (
            ("none", "Never (always pause when idle)"),
            ("vw_foreground", "Vectorworks is still the active app"),
            ("vw_file_open", "Vectorworks file is still open"),
            ("log_open", "Vectorworks log shows file as open"),
        ):
            self.idle_bypass_mode.addItem(label, mode)
        saved_bypass = settings.value("idle_bypass_mode", DEFAULT_IDLE_BYPASS_MODE, type=str)
        if saved_bypass not in IDLE_BYPASS_MODES:
            saved_bypass = DEFAULT_IDLE_BYPASS_MODE
        bypass_index = self.idle_bypass_mode.findData(saved_bypass)
        if bypass_index >= 0:
            self.idle_bypass_mode.setCurrentIndex(bypass_index)
        self.idle_bypass_mode.setToolTip(
            "When idle, optionally keep the live timer running if a file remains open. "
            "Vectorworks must still be foreground unless you choose the file-open option."
        )
        form.addRow("When idle, keep tracking if…", self.idle_bypass_mode)

        idle_help = QLabel(IDLE_TIMEOUT_HELPER_TEXT)
        idle_help.setWordWrap(True)
        idle_help.setObjectName("muted")
        form.addRow("", idle_help)
        self._sync_idle_controls(self.idle_pause_enabled.isChecked())

        self.auto_track = QCheckBox("Auto-track active file")
        self.auto_track.setChecked(settings.value("auto_track_enabled", True, type=bool))
        form.addRow("", self.auto_track)

        self.dark_mode = QCheckBox("Use dark mode")
        self.dark_mode.setChecked(settings.value("dark_mode_enabled", False, type=bool))
        form.addRow("", self.dark_mode)

        self.import_log_history = QCheckBox("Import Vectorworks log history")
        self.import_log_history.setChecked(settings.value("import_vw_log_history", True, type=bool))
        form.addRow("", self.import_log_history)

        self.merge_years = QCheckBox("Merge other years")
        self.merge_years.setChecked(settings.value("vw_log_merge_years", True, type=bool))
        form.addRow("", self.merge_years)

        form.addRow("", QLabel("Cross-machine log sync"))
        self.sync_enabled = QCheckBox("Enable cross-machine log sync")
        self.sync_enabled.setChecked(settings.value("sync_enabled", False, type=bool))
        form.addRow("", self.sync_enabled)

        sync_row = QWidget()
        sync_row_layout = QHBoxLayout(sync_row)
        sync_row_layout.setContentsMargins(0, 0, 0, 0)
        self.sync_folder = QLineEdit(settings.value("sync_folder", "", type=str))
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_sync_folder)
        sync_row_layout.addWidget(self.sync_folder)
        sync_row_layout.addWidget(browse_btn)
        form.addRow("Sync folder", sync_row)

        self.vw_identity = resolve_vw_identity(refresh=True)
        identity_text = (
            f"License: {self.vw_identity.license_id or 'unknown'} · "
            f"Machine UUID: {self.vw_identity.machine_uuid or 'not found'}"
        )
        identity_label = QLabel(identity_text)
        identity_label.setWordWrap(True)
        identity_label.setToolTip(
            "Derived from Vectorworks AppData (machine_uuid.txt and VW User Log). "
            "Used to identify this computer in cross-machine sync."
        )
        form.addRow("Vectorworks identity", identity_label)

        stored_machine_id = settings.value("sync_machine_id", default_machine_id(), type=str)
        resolved_machine_id = resolve_sync_machine_id(str(stored_machine_id))
        self.machine_id = QLineEdit(resolved_machine_id)
        self.machine_id.setReadOnly(True)
        self.machine_id.setToolTip("Stable ID from Vectorworks machine_uuid.txt")
        form.addRow("Machine ID", self.machine_id)

        stored_label = settings.value("sync_machine_label", "", type=str)
        self.machine_label = QLineEdit(resolve_sync_machine_label(str(stored_label)))
        self.machine_label.setPlaceholderText(self.vw_identity.default_label)
        form.addRow("Machine label", self.machine_label)

        self.sync_on_refresh = QCheckBox("Sync when refreshing log data")
        self.sync_on_refresh.setChecked(settings.value("sync_on_refresh", True, type=bool))
        form.addRow("", self.sync_on_refresh)

        self.minimize_to_tray = QCheckBox("Minimize to tray on close")
        self.minimize_to_tray.setChecked(settings.value("minimize_to_tray", True, type=bool))
        form.addRow("", self.minimize_to_tray)

        self.notifications_enabled = QCheckBox("Enable desktop notifications")
        self.notifications_enabled.setChecked(settings.value("notifications_enabled", True, type=bool))
        form.addRow("", self.notifications_enabled)

        self.global_hotkeys = QCheckBox("Enable global hotkeys (Ctrl+Shift+P/M/R/H)")
        self.global_hotkeys.setChecked(settings.value("global_hotkeys_enabled", True, type=bool))
        form.addRow("", self.global_hotkeys)

        self.eod_notify = QCheckBox("Enable end-of-day summary notification")
        self.eod_notify.setChecked(settings.value("eod_notify_enabled", True, type=bool))
        form.addRow("", self.eod_notify)

        self.eod_hour = QSpinBox()
        self.eod_hour.setRange(0, 23)
        self.eod_hour.setValue(int(settings.value("eod_notify_hour", 17, type=int)))
        form.addRow("End-of-day hour (24h)", self.eod_hour)

        self.portable_mode = QCheckBox("Portable mode (store data next to app)")
        self.portable_mode.setChecked(settings.value("portable_mode", False, type=bool))
        if SHOW_PORTABLE_MODE_UI:
            form.addRow("", self.portable_mode)
        else:
            self.portable_mode.hide()

        self.autostart = QCheckBox("Start VectorTrack in the system tray when Windows starts")
        self.autostart.setChecked(settings.value("autostart_enabled", autostart_is_enabled(), type=bool))
        form.addRow("", self.autostart)

        if ENFORCE_LICENSING:
            form.addRow("License", QLabel("Licensing is enforced in this build."))

        layout.addLayout(form)
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def _sync_idle_controls(self, enabled: bool) -> None:
        self.idle_minutes.setEnabled(enabled)
        self.idle_bypass_mode.setEnabled(enabled)

    def _browse_sync_folder(self) -> None:
        start = self.sync_folder.text().strip()
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select cloud sync folder (Google Drive, Dropbox, OneDrive, etc.)",
            start,
        )
        if folder:
            self.sync_folder.setText(folder)

    def values(self) -> dict[str, object]:
        return {
            "default_hourly_rate": self.default_rate.value(),
            "idle_pause_enabled": self.idle_pause_enabled.isChecked(),
            "default_idle_timeout": self.idle_minutes.value(),
            "idle_bypass_mode": self.idle_bypass_mode.currentData(),
            "auto_track_enabled": self.auto_track.isChecked(),
            "dark_mode_enabled": self.dark_mode.isChecked(),
            "import_vw_log_history": self.import_log_history.isChecked(),
            "vw_log_merge_years": self.merge_years.isChecked(),
            "sync_enabled": self.sync_enabled.isChecked(),
            "sync_folder": self.sync_folder.text().strip(),
            "sync_machine_id": resolve_sync_machine_id(self.machine_id.text()),
            "sync_machine_label": resolve_sync_machine_label(self.machine_label.text()),
            "sync_on_refresh": self.sync_on_refresh.isChecked(),
            "minimize_to_tray": self.minimize_to_tray.isChecked(),
            "notifications_enabled": self.notifications_enabled.isChecked(),
            "global_hotkeys_enabled": self.global_hotkeys.isChecked(),
            "eod_notify_enabled": self.eod_notify.isChecked(),
            "eod_notify_hour": self.eod_hour.value(),
            "portable_mode": self.portable_mode.isChecked() if SHOW_PORTABLE_MODE_UI else False,
            "autostart_enabled": self.autostart.isChecked(),
        }
