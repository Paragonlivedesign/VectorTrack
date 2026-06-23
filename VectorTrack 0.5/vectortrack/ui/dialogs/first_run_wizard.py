"""First-run setup wizard."""

from __future__ import annotations

from PyQt6.QtCore import QSettings

from vectortrack.config import DEFAULT_IDLE_PAUSE_ENABLED, IDLE_TIMEOUT_HELPER_TEXT, format_version
from PyQt6.QtWidgets import (
    QCheckBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)


class FirstRunWizard(QWizard):
    def __init__(self, settings: QSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("VectorTrack Setup Wizard")
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)

        self.import_logs_check = QCheckBox("Import Vectorworks log history")
        self.import_logs_check.setChecked(settings.value("import_vw_log_history", True, type=bool))
        self.merge_years_check = QCheckBox("Merge prior-year logs")
        self.merge_years_check.setChecked(settings.value("vw_log_merge_years", True, type=bool))
        self.auto_track_check = QCheckBox("Enable auto-tracking")
        self.auto_track_check.setChecked(settings.value("auto_track_enabled", True, type=bool))
        self.minimize_tray_check = QCheckBox("Minimize to tray on close")
        self.minimize_tray_check.setChecked(settings.value("minimize_to_tray", True, type=bool))
        self.dark_mode_check = QCheckBox("Use dark mode")
        self.dark_mode_check.setChecked(settings.value("dark_mode_enabled", False, type=bool))
        self.idle_pause_enabled = QCheckBox("Pause tracking when idle")
        self.idle_pause_enabled.setChecked(
            settings.value("idle_pause_enabled", DEFAULT_IDLE_PAUSE_ENABLED, type=bool)
        )
        self.idle_pause_enabled.toggled.connect(self._sync_idle_controls)
        self.idle_minutes = QSpinBox()
        self.idle_minutes.setRange(1, 120)
        self.idle_minutes.setValue(settings.value("default_idle_timeout", 5, type=int))

        self._build_pages()
        self.finished.connect(self._save_values)

    def _build_pages(self) -> None:
        self.addPage(
            self._page(
                "Welcome",
                f"Welcome to {format_version(include_product_name=True)}.\n\n"
                "VectorTrack will try to find Vectorworks automatically. If it cannot, "
                "you will be prompted to select Vectorworks.exe. Historical hours are read "
                "from Vectorworks Log.txt in your AppData folder.",
            )
        )
        self.addPage(self._checkbox_page("Tracking", "Choose how tracking should run.", self.auto_track_check))
        self.addPage(self._checkbox_page("Log Imports", "Configure historical log import behavior.", self.import_logs_check))
        self.addPage(self._checkbox_page("Merge Years", "Include previous years when scanning logs.", self.merge_years_check))
        self.addPage(self._checkbox_page("Tray Behavior", "Choose close behavior.", self.minimize_tray_check))
        self.addPage(self._appearance_page())
        self.addPage(self._page("Finish", "Click Finish to save these defaults.\nYou can update settings any time."))

    @staticmethod
    def _page(title: str, text: str) -> QWizardPage:
        page = QWizardPage()
        page.setTitle(title)
        layout = QVBoxLayout(page)
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch()
        return page

    @staticmethod
    def _checkbox_page(title: str, text: str, checkbox: QCheckBox) -> QWizardPage:
        page = QWizardPage()
        page.setTitle(title)
        layout = QVBoxLayout(page)
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addWidget(checkbox)
        layout.addStretch()
        return page

    def _appearance_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Appearance and Idle")
        layout = QVBoxLayout(page)
        layout.addWidget(self.dark_mode_check)
        layout.addWidget(self.idle_pause_enabled)
        idle_label = QLabel("Idle timeout (minutes)")
        layout.addWidget(idle_label)
        layout.addWidget(self.idle_minutes)
        idle_help = QLabel(IDLE_TIMEOUT_HELPER_TEXT)
        idle_help.setWordWrap(True)
        layout.addWidget(idle_help)
        self._sync_idle_controls(self.idle_pause_enabled.isChecked())
        layout.addStretch()
        return page

    def _sync_idle_controls(self, enabled: bool) -> None:
        self.idle_minutes.setEnabled(enabled)

    def _save_values(self) -> None:
        self.settings.setValue("auto_track_enabled", self.auto_track_check.isChecked())
        self.settings.setValue("import_vw_log_history", self.import_logs_check.isChecked())
        self.settings.setValue("vw_log_merge_years", self.merge_years_check.isChecked())
        self.settings.setValue("minimize_to_tray", self.minimize_tray_check.isChecked())
        self.settings.setValue("dark_mode_enabled", self.dark_mode_check.isChecked())
        self.settings.setValue("idle_pause_enabled", self.idle_pause_enabled.isChecked())
        self.settings.setValue("default_idle_timeout", self.idle_minutes.value())
        self.settings.setValue("wizard_completed", True)
