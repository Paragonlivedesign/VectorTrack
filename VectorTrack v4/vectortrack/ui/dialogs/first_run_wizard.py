"""First-run setup wizard."""

from __future__ import annotations

from PyQt6.QtCore import QSettings, Qt

from vectortrack.config import format_version
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWizard,
    QWizardPage,
    QWidget,
)


class FirstRunWizard(QWizard):
    def __init__(self, settings: QSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("VectorTrack Setup Wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setMinimumSize(640, 480)
        self.resize(720, 520)

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
        self.idle_minutes = QSpinBox()
        self.idle_minutes.setRange(1, 120)
        self.idle_minutes.setValue(settings.value("default_idle_timeout", 5, type=int))
        self.idle_minutes.setMinimumWidth(120)

        self._build_pages()
        self.finished.connect(self._save_values)

    def _build_pages(self) -> None:
        self.addPage(
            self._text_page(
                "Welcome",
                f"Welcome to {format_version(include_product_name=True)}",
                "VectorTrack tracks time on your open Vectorworks files automatically.\n\n"
                "This short wizard sets a few defaults. You can change everything later in Settings.",
            )
        )
        self.addPage(self._tracking_page())
        self.addPage(self._appearance_page())
        self.addPage(
            self._text_page(
                "Finish",
                "You're all set",
                "Click Finish to save these defaults and start using VectorTrack.",
            )
        )

    @staticmethod
    def _styled_label(text: str, *, title: bool = False) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setMinimumWidth(520)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        if title:
            label.setStyleSheet("font-size: 14pt; font-weight: 600; margin-bottom: 8px;")
        else:
            label.setStyleSheet("font-size: 10pt; line-height: 1.35;")
        return label

    @classmethod
    def _text_page(cls, name: str, heading: str, body: str) -> QWizardPage:
        page = QWizardPage()
        page.setTitle(name)
        page.setSubTitle(heading)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(cls._styled_label(body))
        layout.addStretch()
        return page

    def _tracking_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Tracking")
        page.setSubTitle("How VectorTrack should watch your work")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)
        layout.addWidget(
            self._styled_label(
                "Choose whether VectorTrack starts tracking automatically and how it reads "
                "your Vectorworks log files."
            )
        )
        for checkbox in (
            self.auto_track_check,
            self.import_logs_check,
            self.merge_years_check,
            self.minimize_tray_check,
        ):
            checkbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            layout.addWidget(checkbox)
        layout.addStretch()
        return page

    def _appearance_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Appearance")
        page.setSubTitle("Theme and idle timeout")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)
        layout.addWidget(self._styled_label("Pick a theme and how long to wait before pausing for idle time."))
        layout.addWidget(self.dark_mode_check)
        form_host = QWidget(page)
        form = QFormLayout(form_host)
        form.setContentsMargins(0, 8, 0, 0)
        form.addRow("Idle timeout (minutes)", self.idle_minutes)
        layout.addWidget(form_host)
        layout.addStretch()
        return page

    def _save_values(self) -> None:
        self.settings.setValue("auto_track_enabled", self.auto_track_check.isChecked())
        self.settings.setValue("import_vw_log_history", self.import_logs_check.isChecked())
        self.settings.setValue("vw_log_merge_years", self.merge_years_check.isChecked())
        self.settings.setValue("minimize_to_tray", self.minimize_tray_check.isChecked())
        self.settings.setValue("dark_mode_enabled", self.dark_mode_check.isChecked())
        self.settings.setValue("default_idle_timeout", self.idle_minutes.value())
        self.settings.setValue("wizard_completed", True)