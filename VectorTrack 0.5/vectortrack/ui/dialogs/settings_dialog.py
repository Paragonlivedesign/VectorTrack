"""Global settings dialog for VectorTrack."""

from __future__ import annotations

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QCheckBox,
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

from vectortrack.config import DEFAULT_HOURLY_RATE, DEFAULT_IDLE_MINUTES, ENFORCE_LICENSING
from vectortrack.services.autostart import is_enabled as autostart_is_enabled
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

        self.idle_minutes = QSpinBox()
        self.idle_minutes.setRange(1, 240)
        self.idle_minutes.setValue(settings.value("default_idle_timeout", DEFAULT_IDLE_MINUTES, type=int))
        form.addRow("Idle timeout (minutes)", self.idle_minutes)

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

        self.machine_id = QLineEdit(settings.value("sync_machine_id", default_machine_id(), type=str))
        form.addRow("Machine ID", self.machine_id)

        self.machine_label = QLineEdit(settings.value("sync_machine_label", "", type=str))
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
        form.addRow("", self.portable_mode)

        self.autostart = QCheckBox("Start VectorTrack when Windows starts")
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
            "default_idle_timeout": self.idle_minutes.value(),
            "auto_track_enabled": self.auto_track.isChecked(),
            "dark_mode_enabled": self.dark_mode.isChecked(),
            "import_vw_log_history": self.import_log_history.isChecked(),
            "vw_log_merge_years": self.merge_years.isChecked(),
            "sync_enabled": self.sync_enabled.isChecked(),
            "sync_folder": self.sync_folder.text().strip(),
            "sync_machine_id": self.machine_id.text().strip() or default_machine_id(),
            "sync_machine_label": self.machine_label.text().strip(),
            "sync_on_refresh": self.sync_on_refresh.isChecked(),
            "minimize_to_tray": self.minimize_to_tray.isChecked(),
            "notifications_enabled": self.notifications_enabled.isChecked(),
            "global_hotkeys_enabled": self.global_hotkeys.isChecked(),
            "eod_notify_enabled": self.eod_notify.isChecked(),
            "eod_notify_hour": self.eod_hour.value(),
            "portable_mode": self.portable_mode.isChecked(),
            "autostart_enabled": self.autostart.isChecked(),
        }
