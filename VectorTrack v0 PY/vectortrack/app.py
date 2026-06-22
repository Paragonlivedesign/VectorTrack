"""
Main application module for VectorTrack.
"""

import sys
import os
import platform
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QPushButton, QLineEdit,
                            QSpinBox, QDoubleSpinBox, QMessageBox, QFileDialog,
                            QInputDialog, QListWidget, QCheckBox, QListWidgetItem,
                            QMenuBar, QMenu, QTextEdit, QDialog, QTableWidget, QTableWidgetItem,
                            QGroupBox, QScrollArea, QColorDialog, QStyle)
from PyQt6.QtCore import Qt, QTimer, QSettings, QUrl
from PyQt6.QtGui import QPalette, QColor, QDesktopServices
from loguru import logger

from . import __version__
from .process_monitor import ProcessMonitor
from .activity_monitor import ActivityMonitor
from .session_logger import SessionLogger, TimeSession
from .licensing import LicenseManager

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About VectorTrack")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Version info
        version_label = QLabel(f"VectorTrack v{__version__}")
        version_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        # Description
        desc_label = QLabel(
            "Professional time tracking software for Vectorworks projects.\n"
            "Automatically tracks your work time and generates detailed reports."
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)
        
        # Contact info
        contact_label = QLabel(
            "\nContact Information:\n"
            "Email: support@vectortrack.com\n"
            "Website: www.vectortrack.com"
        )
        contact_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(contact_label)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

class BugReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Submit Bug Report")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Description label
        desc_label = QLabel(
            "Please describe the issue you encountered. "
            "Include as much detail as possible."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Bug description input
        self.description_edit = QTextEdit()
        layout.addWidget(self.description_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self._submit_report)
        button_layout.addWidget(submit_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
    def _submit_report(self):
        """Submit the bug report."""
        description = self.description_edit.toPlainText()
        if not description.strip():
            QMessageBox.warning(self, "Error", "Please enter a description of the issue.")
            return
            
        # Get system information
        system_info = (
            f"\n\nSystem Information:\n"
            f"OS: {platform.system()} {platform.version()}\n"
            f"Python: {platform.python_version()}\n"
            f"VectorTrack: v{__version__}\n"
            f"Qt: {QApplication.instance().applicationVersion()}\n"
        )
        
        # For now, open email client with pre-filled report
        url = QUrl(
            f"mailto:support@vectortrack.com?"
            f"subject=VectorTrack Bug Report v{__version__}&"
            f"body={description}{system_info}"
        )
        QDesktopServices.openUrl(url)
        self.accept()

class FileSettingsDialog(QDialog):
    def __init__(self, file_path, idle_timeout_minutes=5, hourly_rate=75.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Settings - {os.path.basename(file_path)}")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Rate Setting
        rate_group = QWidget()
        rate_layout = QHBoxLayout(rate_group)
        
        rate_label = QLabel("Hourly Rate ($):")
        rate_layout.addWidget(rate_label)
        
        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0, 1000)
        self.rate_input.setValue(hourly_rate)
        self.rate_input.setDecimals(2)
        self.rate_input.setSingleStep(1.0)
        rate_layout.addWidget(self.rate_input)
        
        layout.addWidget(rate_group)
        
        # Idle Timeout Setting
        idle_group = QWidget()
        idle_layout = QHBoxLayout(idle_group)
        
        idle_label = QLabel("Idle Timeout (minutes):")
        idle_layout.addWidget(idle_label)
        
        self.idle_timeout_input = QSpinBox()
        self.idle_timeout_input.setRange(1, 60)
        self.idle_timeout_input.setValue(idle_timeout_minutes)
        idle_layout.addWidget(self.idle_timeout_input)
        
        layout.addWidget(idle_group)
        
        # Buttons
        button_box = QHBoxLayout()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        button_box.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(cancel_button)
        
        layout.addLayout(button_box)
        
    def get_settings(self):
        return {
            'idle_timeout_minutes': self.idle_timeout_input.value(),
            'hourly_rate': self.rate_input.value()
        }

class FileItemWidget(QWidget):
    def __init__(self, file_path, session, is_tracked, is_paused, hourly_rate, activity_monitor=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.idle_timeout_minutes = 5  # Default idle timeout
        self.session = session  # Store session reference
        self.activity_monitor = activity_monitor  # Store activity monitor reference
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Main container with background
        container = QWidget()
        container.setObjectName("fileItemContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(8)
        
        # Top row: File name, status and controls
        top_row = QHBoxLayout()
        
        # File info section
        info_section = QVBoxLayout()
        info_section.setSpacing(4)
        
        # File name with icon
        name_row = QHBoxLayout()
        file_icon = QLabel()
        file_icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon).pixmap(16, 16))
        name_row.addWidget(file_icon)
        
        file_name = os.path.basename(file_path)
        name_label = QLabel(file_name)
        name_label.setObjectName("fileName")
        name_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        name_row.addWidget(name_label)
        name_row.addStretch()
        info_section.addLayout(name_row)
        
        # Status indicator with icon
        status_row = QHBoxLayout()
        self.status_icon = QLabel()
        status_row.addWidget(self.status_icon)
        
        self.status_label = QLabel()
        self.status_label.setObjectName("statusLabel")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        info_section.addLayout(status_row)
        
        top_row.addLayout(info_section, stretch=1)
        
        # Controls section
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        
        # Rate display with currency icon
        rate_layout = QVBoxLayout()
        rate_layout.setSpacing(4)
        rate_row = QHBoxLayout()
        rate_icon = QLabel()
        rate_icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton).pixmap(12, 12))
        rate_row.addWidget(rate_icon)
        rate_label = QLabel("Hourly Rate")
        rate_label.setObjectName("rateLabel")
        rate_row.addWidget(rate_label)
        rate_layout.addLayout(rate_row)
        
        self.rate_display = QLabel(f"${hourly_rate:.2f}/hr")
        self.rate_display.setObjectName("rateDisplay")
        self.rate_display.setStyleSheet("font-size: 12pt; font-weight: bold;")
        rate_layout.addWidget(self.rate_display)
        controls_layout.addLayout(rate_layout)
        
        # Buttons group with icons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)
        
        # Top row of buttons
        top_buttons = QHBoxLayout()
        top_buttons.setSpacing(8)
        
        # Pause button with icon
        self.pause_button = QPushButton()
        self.pause_button.setIcon(self.style().standardIcon(
            QStyle.StandardPixmap.SP_MediaPause if not is_paused else QStyle.StandardPixmap.SP_MediaPlay))
        self.pause_button.setText("Pause" if not is_paused else "Resume")
        self.pause_button.setObjectName("pauseButton")
        self.pause_button.setCheckable(True)
        self.pause_button.setChecked(is_paused)
        self.pause_button.setMinimumWidth(90)
        top_buttons.addWidget(self.pause_button)
        
        # View Log button with icon
        self.log_button = QPushButton()
        self.log_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.log_button.setText("View Log")
        self.log_button.setObjectName("logButton")
        self.log_button.setMinimumWidth(90)
        top_buttons.addWidget(self.log_button)
        
        buttons_layout.addLayout(top_buttons)
        
        # Bottom row of buttons
        bottom_buttons = QHBoxLayout()
        bottom_buttons.setSpacing(8)
        
        # Settings button with icon
        self.settings_button = QPushButton()
        self.settings_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView))
        self.settings_button.setText("Settings")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.setMinimumWidth(90)
        bottom_buttons.addWidget(self.settings_button)
        
        # Generate Report button with icon
        self.report_button = QPushButton()
        self.report_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self.report_button.setText("Report")
        self.report_button.setObjectName("reportButton")
        self.report_button.setMinimumWidth(90)
        bottom_buttons.addWidget(self.report_button)
        
        buttons_layout.addLayout(bottom_buttons)
        controls_layout.addLayout(buttons_layout)
        
        top_row.addLayout(controls_layout)
        container_layout.addLayout(top_row)
        
        # Stats row with icons
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        # Time stats with clock icon
        time_row = QHBoxLayout()
        time_icon = QLabel()
        time_icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation).pixmap(16, 16))
        time_row.addWidget(time_icon)
        self.time_label = QLabel()
        self.time_label.setObjectName("timeLabel")
        time_row.addWidget(self.time_label)
        stats_layout.addLayout(time_row)
        
        # Money stats with money icon
        money_row = QHBoxLayout()
        money_icon = QLabel()
        money_icon.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton).pixmap(16, 16))
        money_row.addWidget(money_icon)
        self.money_label = QLabel()
        self.money_label.setObjectName("moneyLabel")
        money_row.addWidget(self.money_label)
        stats_layout.addLayout(money_row)
        
        stats_layout.addStretch()
        container_layout.addLayout(stats_layout)
        
        layout.addWidget(container)
        
        # Connect settings button
        self.settings_button.clicked.connect(self._show_settings_dialog)
        
        # Initial update
        self.update_status(is_tracked, is_paused)
        self.update_stats()
        
    def update_status(self, is_tracked: bool, is_paused: bool):
        """Update the status display."""
        if is_paused:
            status = "Paused"
            status_color = "#FFA500"  # Orange
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        else:
            is_idle = not self.activity_monitor.is_active() if hasattr(self, 'activity_monitor') else False
            if is_tracked:
                if is_idle:
                    status = "Idle"
                    status_color = "#9E9E9E"  # Gray
                    icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
                else:
                    status = "Active"
                    status_color = "#4CAF50"  # Green
                    icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
            else:
                status = "Idle"
                status_color = "#9E9E9E"  # Gray
                icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
        
        self.status_icon.setPixmap(icon.pixmap(16, 16))
        self.status_label.setText(f"Status: {status}")
        self.status_label.setStyleSheet(f"""
            color: {status_color};
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 2px;
            background: rgba({int(status_color[1:3], 16)}, 
                           {int(status_color[3:5], 16)}, 
                           {int(status_color[5:7], 16)}, 0.1);
        """)
        
        # Update pause button icon
        self.pause_button.setIcon(self.style().standardIcon(
            QStyle.StandardPixmap.SP_MediaPause if not is_paused else QStyle.StandardPixmap.SP_MediaPlay))
        self.pause_button.setText("Pause" if not is_paused else "Resume")
        
    def update_stats(self):
        """Update time and money statistics."""
        if self.session:
            # Time stats
            total_seconds = self.session.active_duration.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            
            # Format time with appropriate units
            if hours > 0:
                time_text = f"Time: {hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                time_text = f"Time: {minutes}m {seconds}s"
            else:
                time_text = f"Time: {seconds}s"
            
            self.time_label.setText(time_text)
            
            # Calculate hourly progress
            hour_progress = (total_seconds % 3600) / 3600
            tooltip_text = f"Session Details:\n"
            tooltip_text += f"Total Time: {hours:02d}:{minutes:02d}:{seconds:02d}\n"
            tooltip_text += f"Hourly Progress: {hour_progress:.1%}\n"
            tooltip_text += f"Rate: ${self.session.hourly_rate:.2f}/hr\n"
            tooltip_text += f"Earned: ${self.session.billable_amount:.2f}"
            
            self.time_label.setToolTip(tooltip_text)
            
            # Money stats with appropriate formatting
            earned = self.session.billable_amount
            if earned >= 1000:
                money_text = f"Earned: ${earned:,.2f}"
            else:
                money_text = f"Earned: ${earned:.2f}"
            
            self.money_label.setText(money_text)
            
            # Add tooltip with rate details
            rate_tooltip = f"Billable Amount: ${earned:.2f}\n"
            rate_tooltip += f"Current Rate: ${self.session.hourly_rate:.2f}/hr\n"
            rate_tooltip += f"Time Billed: {hours:02d}:{minutes:02d}:{seconds:02d}"
            self.money_label.setToolTip(rate_tooltip)
            
            # Update container style based on tracking state
            if self.session.active_duration.total_seconds() > 0:
                self.setStyleSheet("""
                    QWidget#fileItemContainer {
                        background-color: rgba(76, 175, 80, 0.05);
                        border: 1px solid rgba(76, 175, 80, 0.2);
                        border-radius: 4px;
                    }
                """)
            else:
                self.setStyleSheet("""
                    QWidget#fileItemContainer {
                        background-color: rgba(158, 158, 158, 0.05);
                        border: 1px solid rgba(158, 158, 158, 0.2);
                        border-radius: 4px;
                    }
                """)
        else:
            self.time_label.setText("Time: --:--:--")
            self.money_label.setText("Earned: $0.00")
            self.time_label.setToolTip("No active session")
            self.money_label.setToolTip("No earnings recorded")
            
            # Reset container style
            self.setStyleSheet("""
                QWidget#fileItemContainer {
                    background-color: rgba(158, 158, 158, 0.05);
                    border: 1px solid rgba(158, 158, 158, 0.2);
                    border-radius: 4px;
                }
            """)

    def update_rate_display(self, rate: float):
        """Update the rate display label."""
        self.rate_display.setText(f"${rate:.2f}/hr")
        self.rate_display.setToolTip(f"Current hourly rate: ${rate:.2f}")
        
        # Update the container style based on rate
        if rate > 0:
            self.rate_display.setStyleSheet("""
                font-size: 12pt;
                font-weight: bold;
                color: #4CAF50;
            """)
        else:
            self.rate_display.setStyleSheet("""
                font-size: 12pt;
                font-weight: bold;
                color: #9E9E9E;
            """)
        
    def _show_settings_dialog(self):
        """Show settings dialog for this file."""
        dialog = FileSettingsDialog(
            self.file_path,
            idle_timeout_minutes=self.idle_timeout_minutes,
            hourly_rate=self.session.hourly_rate if self.session else 75.0,
            parent=self
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.get_settings()
            self.idle_timeout_minutes = settings['idle_timeout_minutes']
            
            # Get the main window instance
            main_window = None
            parent = self.parent()
            while parent:
                if isinstance(parent, MainWindow):
                    main_window = parent
                    break
                parent = parent.parent()
            
            # Update rate if file is paused or not being tracked
            is_tracked = main_window and self.file_path == main_window.tracked_file_path if main_window else False
            is_paused = main_window.is_paused if main_window and is_tracked else False
            
            if not is_tracked or is_paused:
                old_rate = self.session.hourly_rate if self.session else 75.0
                new_rate = float(settings['hourly_rate'])
                if new_rate != old_rate:
                    if self.session:
                        self.session.hourly_rate = new_rate
                        logger.info(f"Rate changed for {self.file_path} from ${old_rate:.2f} to ${new_rate:.2f}")
                    self.update_rate_display(new_rate)
            else:
                QMessageBox.warning(self, "Rate Change Not Allowed",
                                  "The hourly rate can only be changed when the file is paused or not being tracked.")
            
            logger.info(f"Updated settings for {self.file_path} - "
                       f"Idle timeout: {self.idle_timeout_minutes}m")

class SessionLogDialog(QDialog):
    def __init__(self, file_path, session, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Session Log - {os.path.basename(file_path)}")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Session info header
        info_layout = QHBoxLayout()
        
        # File info
        file_info = QLabel(f"File: {os.path.basename(file_path)}")
        info_layout.addWidget(file_info)
        
        # Time info
        if session:
            total_seconds = session.active_duration.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            time_info = QLabel(f"Total Time: {hours:02d}:{minutes:02d}")
            info_layout.addWidget(time_info)
            
            # Money info
            money_info = QLabel(f"Total Earned: ${session.billable_amount:.2f}")
            info_layout.addWidget(money_info)
        
        layout.addLayout(info_layout)
        
        # Session log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                background-color: #1E1E1E;
                color: #FFFFFF;
                padding: 8px;
            }
        """)
        layout.addWidget(self.log_text)
        
        # Load session log
        self._load_session_log(file_path, session)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
    def _load_session_log(self, file_path, session):
        """Load and display the session log."""
        log_dir = Path("logs")
        content = []
        
        # Add session header
        content.append("Session Log")
        content.append("=" * 50)
        content.append("")
        
        # Add session details if available
        if session:
            content.append("Current Session Details:")
            content.append(f"Project ID: {session.project_id}")
            content.append(f"File: {file_path}")
            content.append(f"Start Time: {session.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if session.end_time:
                content.append(f"End Time: {session.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            content.append(f"Duration: {str(session.active_duration).split('.')[0]}")
            content.append(f"Rate: ${session.hourly_rate:.2f}/hour")
            content.append(f"Billable Amount: ${session.billable_amount:.2f}")
            content.append("")
            
        content.append("Activity Log:")
        content.append("-" * 50)
        
        # Read the main log file
        try:
            log_path = log_dir / "vectortrack.log"
            if log_path.exists():
                with open(log_path, 'r') as f:
                    log_lines = f.readlines()
                    # Filter log entries related to this file
                    for line in log_lines:
                        if file_path in line:
                            content.append(line.strip())
            else:
                content.append("No log file found.")
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            content.append("Error reading log file.")
            
        # Display the content
        self.log_text.setPlainText("\n".join(content))
        
        # Move cursor to start
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        self.log_text.setTextCursor(cursor)

class ApplicationSettingsDialog(QDialog):
    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.setMinimumWidth(600)  # Increased width for new sections
        self.settings = settings
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Create a scroll area to handle many settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(16)
        
        # Default Rate Section
        rate_group = QGroupBox("Default Rate Settings")
        rate_layout = QVBoxLayout(rate_group)
        
        rate_description = QLabel("Set the default hourly rate for new projects:")
        rate_description.setWordWrap(True)
        rate_layout.addWidget(rate_description)
        
        rate_input_layout = QHBoxLayout()
        rate_label = QLabel("Default Hourly Rate ($):")
        rate_input_layout.addWidget(rate_label)
        
        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0, 1000)
        self.rate_input.setValue(self.settings.value("default_hourly_rate", 75.0, type=float))
        self.rate_input.setDecimals(2)
        self.rate_input.setSingleStep(1.0)
        rate_input_layout.addWidget(self.rate_input)
        
        rate_layout.addLayout(rate_input_layout)
        scroll_layout.addWidget(rate_group)
        
        # Idle Timeout Section
        idle_group = QGroupBox("Default Idle Settings")
        idle_layout = QVBoxLayout(idle_group)
        
        idle_description = QLabel("Set the default idle timeout for new projects:")
        idle_description.setWordWrap(True)
        idle_layout.addWidget(idle_description)
        
        idle_input_layout = QHBoxLayout()
        idle_label = QLabel("Default Idle Timeout (minutes):")
        idle_input_layout.addWidget(idle_label)
        
        self.idle_input = QSpinBox()
        self.idle_input.setRange(1, 60)
        self.idle_input.setValue(self.settings.value("default_idle_timeout", 5, type=int))
        idle_layout.addWidget(self.idle_input)
        
        idle_layout.addLayout(idle_input_layout)
        scroll_layout.addWidget(idle_group)
        
        # Auto-start Section
        autostart_group = QGroupBox("Auto-start Settings")
        autostart_layout = QVBoxLayout(autostart_group)
        
        self.autostart_checkbox = QCheckBox("Automatically start tracking new files")
        self.autostart_checkbox.setChecked(self.settings.value("auto_track_enabled", True, type=bool))
        autostart_layout.addWidget(self.autostart_checkbox)
        
        scroll_layout.addWidget(autostart_group)
        
        # Color Palette Section
        color_group = QGroupBox("Color Palette Settings")
        color_layout = QVBoxLayout(color_group)
        
        # Background Colors
        bg_layout = QHBoxLayout()
        bg_label = QLabel("Background Color:")
        bg_layout.addWidget(bg_label)
        
        self.bg_color_button = QPushButton()
        self.bg_color_button.setFixedSize(30, 30)
        bg_color = self.settings.value("custom_bg_color", "#1E1E1E")
        self.bg_color_button.setStyleSheet(f"background-color: {bg_color};")
        self.bg_color_button.clicked.connect(lambda: self._pick_color("background"))
        bg_layout.addWidget(self.bg_color_button)
        
        color_layout.addLayout(bg_layout)
        
        # Accent Colors
        accent_layout = QHBoxLayout()
        accent_label = QLabel("Accent Color:")
        accent_layout.addWidget(accent_label)
        
        self.accent_color_button = QPushButton()
        self.accent_color_button.setFixedSize(30, 30)
        accent_color = self.settings.value("custom_accent_color", "#2196F3")
        self.accent_color_button.setStyleSheet(f"background-color: {accent_color};")
        self.accent_color_button.clicked.connect(lambda: self._pick_color("accent"))
        accent_layout.addWidget(self.accent_color_button)
        
        color_layout.addLayout(accent_layout)
        
        # Reset Colors Button
        reset_colors_button = QPushButton("Reset to Default Colors")
        reset_colors_button.clicked.connect(self._reset_colors)
        color_layout.addWidget(reset_colors_button)
        
        scroll_layout.addWidget(color_group)
        
        # Data Management Section
        data_group = QGroupBox("Data Management")
        data_layout = QVBoxLayout(data_group)
        
        purge_description = QLabel("Clear application data and reset settings. This cannot be undone.")
        purge_description.setWordWrap(True)
        data_layout.addWidget(purge_description)
        
        purge_button = QPushButton("Purge Application Data")
        purge_button.setStyleSheet("background-color: #dc3545; color: white;")
        purge_button.clicked.connect(self._confirm_purge_data)
        data_layout.addWidget(purge_button)
        
        scroll_layout.addWidget(data_group)
        
        # License Information Section
        license_group = QGroupBox("License Information")
        license_layout = QVBoxLayout(license_group)
        
        # Get license info from the parent window's license manager
        parent_window = self.parent()
        if parent_window and hasattr(parent_window, 'license_manager'):
            is_valid, status = parent_window.license_manager.check_license_status()
            license_info = QLabel(f"License Status: {status}")
            license_info.setWordWrap(True)
            license_layout.addWidget(license_info)
            
            if is_valid:
                expiry_date = parent_window.license_manager.get_expiry_date()
                if expiry_date:
                    expiry_label = QLabel(f"Expires: {expiry_date}")
                    license_layout.addWidget(expiry_label)
        
        scroll_layout.addWidget(license_group)
        
        # Add Logs Section
        logs_group = QGroupBox("Application Logs")
        logs_layout = QVBoxLayout(logs_group)
        
        # Log viewer
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMinimumHeight(200)
        self.log_viewer.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                background-color: #1E1E1E;
                color: #FFFFFF;
                padding: 8px;
            }
        """)
        logs_layout.addWidget(self.log_viewer)
        
        # Load latest logs
        self._load_latest_logs()
        
        # Buttons for log management
        log_buttons_layout = QHBoxLayout()
        
        refresh_logs_button = QPushButton("Refresh Logs")
        refresh_logs_button.clicked.connect(self._load_latest_logs)
        log_buttons_layout.addWidget(refresh_logs_button)
        
        export_logs_button = QPushButton("Export Logs")
        export_logs_button.clicked.connect(self._export_logs)
        log_buttons_layout.addWidget(export_logs_button)
        
        logs_layout.addLayout(log_buttons_layout)
        scroll_layout.addWidget(logs_group)
        
        # Add the scroll area to the main layout
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_box = QHBoxLayout()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        button_box.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addWidget(cancel_button)
        
        layout.addLayout(button_box)
        
    def _pick_color(self, color_type):
        """Show color picker dialog and update the button color."""
        current_color = (
            self.settings.value("custom_bg_color", "#1E1E1E")
            if color_type == "background"
            else self.settings.value("custom_accent_color", "#2196F3")
        )
        
        color = QColorDialog.getColor(QColor(current_color), self, f"Select {color_type.title()} Color")
        if color.isValid():
            if color_type == "background":
                self.bg_color_button.setStyleSheet(f"background-color: {color.name()};")
                self.settings.setValue("custom_bg_color", color.name())
            else:
                self.accent_color_button.setStyleSheet(f"background-color: {color.name()};")
                self.settings.setValue("custom_accent_color", color.name())
            
            # Get the main window instance
            parent_window = self.parent()
            if parent_window:
                # Trigger theme reapplication with new colors
                parent_window._apply_theme()
                
    def _reset_colors(self):
        """Reset colors to default values."""
        self.settings.setValue("custom_bg_color", "#1E1E1E")
        self.settings.setValue("custom_accent_color", "#2196F3")
        self.bg_color_button.setStyleSheet("background-color: #1E1E1E;")
        self.accent_color_button.setStyleSheet("background-color: #2196F3;")
        
        # Get the main window instance and reapply theme
        parent_window = self.parent()
        if parent_window:
            parent_window._apply_theme()
    
    def _confirm_purge_data(self):
        """Show confirmation dialog before purging data."""
        response = QMessageBox.warning(
            self,
            "Confirm Data Purge",
            "Are you sure you want to purge all application data? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if response == QMessageBox.StandardButton.Yes:
            self._purge_data()
    
    def _purge_data(self):
        """Purge all application data and settings."""
        try:
            # Clear all settings
            self.settings.clear()
            
            # Reset session data
            parent_window = self.parent()
            if parent_window:
                parent_window.session_logger.clear_all_sessions()
                parent_window.file_sessions = {}
                parent_window.current_session = None
            
            # Clear log files
            log_dir = Path("logs")
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    try:
                        log_file.unlink()
                    except Exception as e:
                        logger.error(f"Failed to delete log file {log_file}: {e}")
            
            QMessageBox.information(
                self,
                "Data Purged",
                "All application data has been successfully purged. The application will now close."
            )
            
            # Close the application
            QApplication.instance().quit()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to purge data: {e}"
            )
    
    def get_settings(self):
        return {
            'default_hourly_rate': self.rate_input.value(),
            'default_idle_timeout': self.idle_input.value(),
            'auto_track_enabled': self.autostart_checkbox.isChecked(),
            'custom_bg_color': self.settings.value("custom_bg_color", "#1E1E1E"),
            'custom_accent_color': self.settings.value("custom_accent_color", "#2196F3")
        }

    def _load_latest_logs(self):
        """Load the latest logs into the viewer."""
        try:
            log_path = Path("logs/vectortrack.log")
            if log_path.exists():
                with open(log_path, 'r') as f:
                    # Read last 1000 lines (adjust as needed)
                    lines = f.readlines()[-1000:]
                    self.log_viewer.setText(''.join(lines))
                    # Scroll to bottom
                    cursor = self.log_viewer.textCursor()
                    cursor.movePosition(cursor.End)
                    self.log_viewer.setTextCursor(cursor)
            else:
                self.log_viewer.setText("No logs found.")
        except Exception as e:
            self.log_viewer.setText(f"Error loading logs: {e}")
            
    def _export_logs(self):
        """Export logs to a file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"vectortrack_logs_{timestamp}.txt"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Logs",
                default_name,
                "Text Files (*.txt);;All Files (*)"
            )
            
            if file_path:
                log_path = Path("logs/vectortrack.log")
                if log_path.exists():
                    # Copy the log file to the selected location
                    with open(log_path, 'r') as source, open(file_path, 'w') as target:
                        target.write(source.read())
                    QMessageBox.information(self, "Success", "Logs exported successfully!")
                else:
                    QMessageBox.warning(self, "Error", "No logs found to export.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export logs: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VectorTrack")
        # Set a larger minimum size for better visibility
        self.setMinimumSize(800, 600)
        # Set a reasonable starting size
        self.resize(1024, 768)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Initialize settings
        self.settings = QSettings("VectorTrack", "VectorTrack")
        
        # Initialize components
        self.process_monitor = ProcessMonitor()
        self.activity_monitor = ActivityMonitor()
        self.session_logger = SessionLogger()
        self.license_manager = LicenseManager()
        
        self.current_session: Optional[TimeSession] = None
        self.last_activity_check = datetime.now()
        self.tracked_file_path: Optional[str] = None
        self.auto_track_enabled = self.settings.value("auto_track_enabled", True, type=bool)
        self.dark_mode_enabled = self.settings.value("dark_mode_enabled", False, type=bool)
        self.is_paused = False
        self.file_sessions = {}  # Store sessions for each file
        
        # Set up UI
        self._setup_ui()
        
        # Apply theme
        self._apply_theme()
        
        # Try to auto-detect Vectorworks
        self._auto_detect_vectorworks()
        
        # Set up timers
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(1000)  # Update every second
        
        # Check license
        self._check_license()
        
        # Start activity monitoring
        self.activity_monitor.add_activity_callback(self._on_activity_change)
        self.activity_monitor.start()
        
        logger.info("Application started")
        
    def _create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                font-size: 11pt;
                font-weight: bold;
                padding: 4px;
                spacing: 8px;
            }
            QMenuBar::item {
                padding: 4px 8px;
                margin: 2px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background-color: #404040;
                color: white;
            }
        """)

        # File Menu
        file_menu = menubar.addMenu('&File')
        file_menu.setStyleSheet("""
            QMenu {
                font-size: 10pt;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
            }
            QMenu::item:selected {
                background-color: #404040;
                color: white;
            }
        """)

        # Add menu items
        settings_action = file_menu.addAction('Settings')
        settings_action.triggered.connect(self._show_settings_dialog)
        file_menu.addSeparator()
        exit_action = file_menu.addAction('Exit')
        exit_action.triggered.connect(self.close)

        # Help Menu
        help_menu = menubar.addMenu('&Help')
        help_menu.setStyleSheet(file_menu.styleSheet())  # Use same styling as file menu

        about_action = help_menu.addAction('About')
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addSeparator()
        report_bug_action = help_menu.addAction('Report Bug')
        report_bug_action.triggered.connect(self._show_bug_report_dialog)
        contact_action = help_menu.addAction('Contact Support')
        contact_action.triggered.connect(self._contact_support)

    def _show_about_dialog(self):
        """Show the About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()
        
    def _show_bug_report_dialog(self):
        """Show the bug report dialog."""
        dialog = BugReportDialog(self)
        dialog.exec()
        
    def _contact_support(self):
        """Open email client to contact support."""
        url = QUrl("mailto:support@vectortrack.com")
        QDesktopServices.openUrl(url)
        
    def _setup_ui(self):
        """Set up the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(12, 12, 12, 12)  # Add more padding around edges
        layout.setSpacing(10)  # Increase spacing between elements
        
        # Settings bar
        settings_bar = QWidget()
        settings_layout = QHBoxLayout(settings_bar)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(20)  # Increase spacing between checkboxes
        
        # Auto-track checkbox
        self.auto_track_checkbox = QCheckBox("Auto-track new files")
        self.auto_track_checkbox.setChecked(self.auto_track_enabled)
        self.auto_track_checkbox.stateChanged.connect(self._toggle_auto_track)
        settings_layout.addWidget(self.auto_track_checkbox)
        
        # Dark mode checkbox
        self.dark_mode_checkbox = QCheckBox("Dark Mode")
        self.dark_mode_checkbox.setChecked(self.dark_mode_enabled)
        self.dark_mode_checkbox.stateChanged.connect(self._toggle_dark_mode)
        settings_layout.addWidget(self.dark_mode_checkbox)
        
        settings_layout.addStretch()  # Push checkboxes to the left
        layout.addWidget(settings_bar)
        
        # Vectorworks executable selection
        vw_group = QWidget()
        vw_layout = QHBoxLayout(vw_group)
        vw_layout.setContentsMargins(0, 0, 0, 0)
        
        self.vw_path_label = QLabel("Vectorworks not selected")
        self.vw_path_label.setMinimumWidth(300)  # Ensure label has enough space
        vw_layout.addWidget(self.vw_path_label)
        
        self.select_vw_button = QPushButton("Select Vectorworks")
        self.select_vw_button.setMinimumWidth(150)  # Set minimum button width
        self.select_vw_button.clicked.connect(self._select_vectorworks)
        vw_layout.addWidget(self.select_vw_button)
        
        vw_layout.addStretch()  # Push elements to the left
        layout.addWidget(vw_group)
        
        # Open files list
        files_group = QWidget()
        files_layout = QVBoxLayout(files_group)
        files_layout.setContentsMargins(0, 0, 0, 0)
        
        files_label = QLabel("Open Files")
        files_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        files_layout.addWidget(files_label)
        
        self.open_files_list = QListWidget()
        self.open_files_list.setSpacing(8)  # Increase spacing between items
        self.open_files_list.setStyleSheet("""
            QListWidget {
                padding: 8px;
                min-height: 200px;
            }
            QListWidget::item {
                padding: 4px;
                margin: 2px 0;
            }
        """)
        self.open_files_list.itemClicked.connect(self._select_file_from_list)
        files_layout.addWidget(self.open_files_list)
        
        layout.addWidget(files_group)
        
        # Project Totals Section
        totals_group = QWidget()
        totals_layout = QVBoxLayout(totals_group)
        totals_layout.setContentsMargins(0, 0, 0, 0)
        
        # Session Summary section
        summary_label = QLabel("Session Summary")
        summary_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
                padding: 10px 0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        self.totals_table = QTableWidget()
        self.totals_table.setColumnCount(4)
        self.totals_table.setHorizontalHeaderLabels(["Project", "Time", "Rate", "Amount"])
        self.totals_table.setStyleSheet("""
            QTableWidget {
                background-color: #2D2D2D;
                border: 1px solid #3B79BC;
                gridline-color: #3B79BC;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTableWidget::item {
                color: #FFFFFF;
                padding: 5px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
            }
            QHeaderView::section {
                background-color: #3B79BC;
                color: #FFFFFF;
                font-weight: bold;
                padding: 5px;
                border: none;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
            }
            QHeaderView::section:horizontal {
                border-right: 1px solid #2D2D2D;
            }
        """)
        
        # Adjust column widths
        self.totals_table.setColumnWidth(0, 300)  # Project column
        self.totals_table.setColumnWidth(1, 100)  # Time column
        self.totals_table.setColumnWidth(2, 100)  # Rate column
        self.totals_table.setColumnWidth(3, 100)  # Amount column
        
        # Make sure headers are always visible
        self.totals_table.horizontalHeader().setVisible(True)
        self.totals_table.horizontalHeader().setHighlightSections(False)
        self.totals_table.verticalHeader().setVisible(False)
        
        totals_layout.addWidget(summary_label)
        totals_layout.addWidget(self.totals_table)
        
        # Grand Total Row
        grand_total_layout = QHBoxLayout()
        grand_total_layout.setSpacing(20)
        
        self.total_time_label = QLabel("Total Time: 00:00:00")
        self.total_time_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        grand_total_layout.addWidget(self.total_time_label)
        
        grand_total_layout.addStretch()
        
        self.total_amount_label = QLabel("Total Amount: $0.00")
        self.total_amount_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        grand_total_layout.addWidget(self.total_amount_label)
        
        totals_layout.addLayout(grand_total_layout)
        
        layout.addWidget(totals_group)
        
        # Control buttons
        button_group = QWidget()
        button_layout = QHBoxLayout(button_group)
        
        self.report_button = QPushButton("Generate Report")
        self.report_button.clicked.connect(self._generate_report)
        button_layout.addWidget(self.report_button)
        
        layout.addWidget(button_group)
        
        # License status
        self.license_label = QLabel()
        self.license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.license_label)
        
        # Activate button
        self.activate_button = QPushButton("Activate License")
        self.activate_button.clicked.connect(self._show_activation_dialog)
        layout.addWidget(self.activate_button)

    def _auto_detect_vectorworks(self):
        """Attempt to automatically detect and select Vectorworks."""
        # First try loading the last used path
        last_path = self.settings.value("vectorworks_path", "")
        if last_path and os.path.exists(last_path):
            try:
                self.process_monitor.set_vectorworks_path(last_path)
                self.vw_path_label.setText(f"Using: {os.path.basename(last_path)}")
                logger.info(f"Loaded last used Vectorworks path: {last_path}")
                return
            except Exception as e:
                logger.error(f"Error loading last Vectorworks path: {e}")
        
        # If last path fails, try auto-detection
        exe_path = self.process_monitor.auto_select_vectorworks()
        if exe_path:
            self.settings.setValue("vectorworks_path", exe_path)
            self.vw_path_label.setText(f"Using: {os.path.basename(exe_path)}")
        else:
            installations = self.process_monitor.find_vectorworks_installations()
            if installations:
                # Show dialog to choose from available versions
                versions = list(installations.keys())
                version, ok = QInputDialog.getItem(
                    self, "Select Vectorworks Version",
                    "Multiple versions found. Please select:",
                    versions, 0, False
                )
                if ok and version:
                    exe_path = installations[version]
                    self.process_monitor.set_vectorworks_path(exe_path)
                    self.settings.setValue("vectorworks_path", exe_path)
                    self.vw_path_label.setText(f"Using: {os.path.basename(exe_path)}")
            
    def _select_vectorworks(self):
        """Show file dialog to select Vectorworks executable."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Vectorworks Executable",
            "",
            "Executable Files (*.exe);;All Files (*)"
        )
        
        if file_path:
            try:
                self.process_monitor.set_vectorworks_path(file_path)
                self.settings.setValue("vectorworks_path", file_path)
                self.vw_path_label.setText(f"Using: {os.path.basename(file_path)}")
                logger.info(f"Selected Vectorworks executable: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Error",
                                  f"Failed to set Vectorworks path: {e}")
                
    def _check_license(self):
        """Check license status and update UI accordingly."""
        is_valid, status = self.license_manager.check_license_status()
        self.license_label.setText(status)
        
        if not is_valid:
            self.report_button.setEnabled(False)
            QMessageBox.warning(self, "License Required",
                              "Your trial period has expired. Please activate the software.")
            
    def _show_activation_dialog(self):
        """Show the license activation dialog."""
        key, ok = QInputDialog.getText(self, "Activate License",
                                  "Enter your license key:")
        if ok and key:
            success, message = self.license_manager.activate_license(key)
            if success:
                self._check_license()
                self.report_button.setEnabled(True)
            QMessageBox.information(self, "Activation Result", message)
            
    def _toggle_tracking(self):
        """Start or stop tracking time."""
        if not self.process_monitor.vectorworks_path:
            QMessageBox.warning(self, "Setup Required",
                              "Please select your Vectorworks executable first.")
            return
            
        if self.current_session is None:
            # Update activity monitor settings
            self.activity_monitor.set_idle_timeout(
                self.idle_timeout_input.value() * 60)  # Convert to seconds
                
            # Start new session
            self.current_session = self.session_logger.start_session(
                project_id="",  # Will be updated when Vectorworks file is detected
                file_path="",  # Will be updated when Vectorworks file is detected
                hourly_rate=self.hourly_rate_input.value()
            )
            
            self.start_button.setText("Stop Tracking")
            self.hourly_rate_input.setEnabled(False)
            self.idle_timeout_input.setEnabled(False)
            self.select_vw_button.setEnabled(False)
            
        else:
            # End current session
            self.session_logger.end_session(self.current_session)
            self.current_session = None
            
            self.start_button.setText("Start Tracking")
            self.hourly_rate_input.setEnabled(True)
            self.idle_timeout_input.setEnabled(True)
            self.select_vw_button.setEnabled(True)
            
    def _apply_theme(self):
        """Apply the current theme (light/dark) to the application."""
        if self.dark_mode_enabled:
            # Get custom colors from settings
            custom_bg = self.settings.value("custom_bg_color", "#2D2D2D")
            custom_accent = self.settings.value("custom_accent_color", "#3B79BC")
            
            # VectorWorks-style dark theme
            palette = QPalette()
            
            # Define colors to match VectorWorks
            background = QColor(custom_bg)      # Main background
            darker_bg = QColor(custom_bg).darker(110)  # Darker panels
            text = QColor("#E0E0E0")           # Main text
            menu_text = QColor("#CCCCCC")      # Menu text
            accent = QColor(custom_accent)      # Accent color
            
            # Main window and text
            palette.setColor(QPalette.ColorRole.Window, background)
            palette.setColor(QPalette.ColorRole.WindowText, text)
            palette.setColor(QPalette.ColorRole.Text, text)
            palette.setColor(QPalette.ColorRole.ButtonText, text)
            
            # Input fields and lists
            palette.setColor(QPalette.ColorRole.Base, darker_bg)
            palette.setColor(QPalette.ColorRole.AlternateBase, background)
            
            # Selection highlighting
            palette.setColor(QPalette.ColorRole.Highlight, accent)
            palette.setColor(QPalette.ColorRole.HighlightedText, text)
            
            # Modern VectorWorks-style dark theme with hard edges
            self.setStyleSheet(f"""
                QMainWindow, QDialog {{
                    background-color: {custom_bg};
                    border: none;
                }}
                
                QWidget {{
                    color: #E0E0E0;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }}
                
                QPushButton {{
                    background-color: {custom_accent};
                    color: white;
                    border: none;
                    border-radius: 0px;
                    padding: 6px 12px;
                    min-height: 20px;
                }}
                
                QPushButton:hover {{
                    background-color: {QColor(custom_accent).lighter(110).name()};
                }}
                
                QPushButton:pressed {{
                    background-color: {QColor(custom_accent).darker(110).name()};
                }}
                
                QMenuBar {{
                    background-color: {custom_bg};
                    border-bottom: 1px solid #222222;
                    padding: 2px;
                }}
                
                QMenuBar::item {{
                    background: transparent;
                    padding: 4px 8px;
                }}
                
                QMenuBar::item:selected {{
                    background-color: {custom_accent};
                }}
                
                QMenu {{
                    background-color: {custom_bg};
                    border: 1px solid #222222;
                    border-radius: 0px;
                }}
                
                QMenu::item {{
                    padding: 6px 20px;
                }}
                
                QMenu::item:selected {{
                    background-color: {custom_accent};
                }}
                
                QListWidget, QTableWidget {{
                    background-color: {QColor(custom_bg).darker(110).name()};
                    border: 1px solid #222222;
                    border-radius: 0px;
                    padding: 0px;
                }}
                
                QListWidget::item, QTableWidget::item {{
                    padding: 4px;
                    border: none;
                }}
                
                QListWidget::item:selected, QTableWidget::item:selected {{
                    background-color: {custom_accent};
                }}
                
                QHeaderView::section {{
                    background-color: {QColor(custom_bg).darker(110).name()};
                    color: #CCCCCC;
                    padding: 4px;
                    border: none;
                    border-right: 1px solid #222222;
                    border-bottom: 1px solid #222222;
                }}
                
                QSpinBox, QDoubleSpinBox {{
                    background-color: {QColor(custom_bg).darker(110).name()};
                    border: 1px solid #222222;
                    border-radius: 0px;
                    padding: 4px;
                    color: #E0E0E0;
                }}
                
                QSpinBox::up-button, QSpinBox::down-button,
                QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                    background-color: {QColor(custom_bg).darker(120).name()};
                    border: none;
                    border-radius: 0px;
                    border-left: 1px solid #222222;
                    width: 16px;
                }}
                
                QSpinBox::up-button:hover, QSpinBox::down-button:hover,
                QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
                    background-color: {custom_accent};
                }}
                
                QCheckBox {{
                    spacing: 8px;
                }}
                
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    background-color: {QColor(custom_bg).darker(110).name()};
                    border: 1px solid #222222;
                    border-radius: 0px;
                }}
                
                QCheckBox::indicator:checked {{
                    background-color: {custom_accent};
                }}
                
                QGroupBox {{
                    border: 1px solid #222222;
                    border-radius: 0px;
                    margin-top: 8px;
                    padding-top: 16px;
                }}
                
                QGroupBox::title {{
                    color: #CCCCCC;
                }}
                
                QScrollBar:vertical {{
                    background-color: {QColor(custom_bg).darker(110).name()};
                    width: 12px;
                    border: none;
                }}
                
                QScrollBar::handle:vertical {{
                    background-color: {QColor(custom_bg).darker(120).name()};
                    min-height: 20px;
                    border: none;
                    border-radius: 0px;
                }}
                
                QScrollBar::handle:vertical:hover {{
                    background-color: {custom_accent};
                }}
                
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                
                QLabel {{
                    color: #E0E0E0;
                }}
                
                #fileItemContainer {{
                    background-color: {QColor(custom_bg).darker(110).name()};
                    border: 1px solid #222222;
                    border-radius: 0px;
                }}
                
                #fileName {{
                    font-size: 12pt;
                    color: #E0E0E0;
                }}
                
                #statusLabel {{
                    color: #CCCCCC;
                }}
            """)
        else:
            # Light theme with hard edges
            palette = QPalette()
            
            # Define colors
            background = QColor("#F0F0F0")      # Main background
            surface = QColor("#FFFFFF")         # Surface color
            text = QColor("#202020")           # Main text
            accent = QColor("#3B79BC")         # Blue accent color
            border = QColor("#D0D0D0")         # Border color
            
            # Set palette colors
            palette.setColor(QPalette.ColorRole.Window, background)
            palette.setColor(QPalette.ColorRole.WindowText, text)
            palette.setColor(QPalette.ColorRole.Text, text)
            palette.setColor(QPalette.ColorRole.ButtonText, text)
            palette.setColor(QPalette.ColorRole.Base, surface)
            palette.setColor(QPalette.ColorRole.AlternateBase, background)
            palette.setColor(QPalette.ColorRole.Highlight, accent)
            palette.setColor(QPalette.ColorRole.HighlightedText, surface)
            
            self.setStyleSheet("""
                QMainWindow, QDialog {
                    background-color: #F0F0F0;
                    border: none;
                }
                
                QWidget {
                    color: #202020;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                
                QPushButton {
                    background-color: white;
                    border: 1px solid #D0D0D0;
                    border-radius: 0px;
                    padding: 6px 12px;
                    color: #202020;
                }
                
                QPushButton:hover {
                    background-color: #F8F8F8;
                    border-color: #3B79BC;
                }
                
                QPushButton:pressed {
                    background-color: #E8E8E8;
                }
                
                QPushButton:checked {
                    background-color: #3B79BC;
                    color: white;
                    border: none;
                }
                
                QListWidget, QTableWidget {
                    background-color: white;
                    border: 1px solid #D0D0D0;
                    border-radius: 0px;
                    padding: 0px;
                }
                
                QListWidget::item, QTableWidget::item {
                    padding: 4px;
                }
                
                QListWidget::item:selected, QTableWidget::item:selected {
                    background-color: #3B79BC;
                    color: white;
                }
                
                QHeaderView::section {
                    background-color: #F0F0F0;
                    color: #202020;
                    padding: 4px;
                    border: none;
                    border-right: 1px solid #D0D0D0;
                    border-bottom: 1px solid #D0D0D0;
                }
                
                QSpinBox, QDoubleSpinBox {
                    background-color: white;
                    border: 1px solid #D0D0D0;
                    border-radius: 0px;
                    padding: 4px;
                }
                
                QSpinBox::up-button, QSpinBox::down-button,
                QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                    background-color: #F0F0F0;
                    border: none;
                    border-radius: 0px;
                    border-left: 1px solid #D0D0D0;
                    width: 16px;
                }
                
                QSpinBox::up-button:hover, QSpinBox::down-button:hover,
                QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                    background-color: #E8E8E8;
                }
                
                QCheckBox {
                    spacing: 8px;
                }
                
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    background-color: white;
                    border: 1px solid #D0D0D0;
                    border-radius: 0px;
                }
                
                QCheckBox::indicator:checked {
                    background-color: #3B79BC;
                    border: none;
                }
                
                QGroupBox {
                    border: 1px solid #D0D0D0;
                    border-radius: 0px;
                    margin-top: 8px;
                    padding-top: 16px;
                    background-color: white;
                }
                
                QScrollBar:vertical {
                    background-color: #F0F0F0;
                    width: 12px;
                    border: none;
                }
                
                QScrollBar::handle:vertical {
                    background-color: #D0D0D0;
                    min-height: 20px;
                    border: none;
                    border-radius: 0px;
                }
                
                QScrollBar::handle:vertical:hover {
                    background-color: #B0B0B0;
                }
                
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                
                #fileItemContainer {
                    background-color: white;
                    border: 1px solid #D0D0D0;
                    border-radius: 0px;
                }
            """)
            
        QApplication.setPalette(palette)
        
    def _toggle_dark_mode(self, state):
        """Toggle dark mode on/off."""
        self.dark_mode_enabled = bool(state)
        self.settings.setValue("dark_mode_enabled", self.dark_mode_enabled)
        self._apply_theme()
        
    def _toggle_auto_track(self, state):
        """Toggle automatic file tracking."""
        self.auto_track_enabled = bool(state)
        self.settings.setValue("auto_track_enabled", self.auto_track_enabled)
        
    def _toggle_pause(self, checked):
        """Pause or resume tracking for the current file."""
        self.is_paused = checked
        if checked:
            self.pause_button.setText("Resume")
            logger.info(f"[STATUS] File tracking paused - {self.tracked_file_path}")
        else:
            self.pause_button.setText("Pause")
            logger.info(f"[STATUS] File tracking resumed - {self.tracked_file_path}")
            
    def _select_file_from_list(self, item):
        """Switch to tracking the selected file."""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and file_path != self.tracked_file_path:
            self._start_tracking_file(file_path)
            
    def _update_open_files_list(self):
        """Update the list of open Vectorworks files."""
        # Store current items to avoid recreating widgets unnecessarily
        current_items = {}
        for i in range(self.open_files_list.count()):
            item = self.open_files_list.item(i)
            widget = self.open_files_list.itemWidget(item)
            if widget:
                current_items[widget.file_path] = (item, widget)
        
        # Get current windows
        windows = self.process_monitor.refresh()
        current_files = set()
        
        for window in windows:
            if window.file_path:
                current_files.add(window.file_path)
                session = self.file_sessions.get(window.file_path)
                is_tracked = window.file_path == self.tracked_file_path
                is_paused = self.is_paused if is_tracked else False
                
                if window.file_path in current_items:
                    # Update existing widget
                    item, widget = current_items[window.file_path]
                    # Update widget state
                    widget.session = session  # Update session reference
                    widget.pause_button.setChecked(is_paused)
                    widget.pause_button.setText("Resume" if is_paused else "Pause")
                    widget.update_status(is_tracked, is_paused)
                    widget.update_stats()
                    if is_tracked:
                        item.setBackground(QColor(220, 237, 220))  # Soft green color
                    else:
                        item.setBackground(QColor(0, 0, 0, 0))  # Clear background
                else:
                    # Create new item and widget
                    item = QListWidgetItem()
                    item.setData(Qt.ItemDataRole.UserRole, window.file_path)
                    widget = FileItemWidget(
                        file_path=window.file_path,
                        session=session,
                        is_tracked=is_tracked,
                        is_paused=is_paused,
                        hourly_rate=session.hourly_rate if session else 75.0,
                        activity_monitor=self.activity_monitor,
                        parent=self.open_files_list
                    )
                    
                    # Connect signals
                    widget.pause_button.clicked.connect(
                        lambda checked, fp=window.file_path: self._toggle_file_pause(fp, checked))
                    widget.log_button.clicked.connect(
                        lambda _, fp=window.file_path: self._show_session_log(fp)
                    )
                    widget.report_button.clicked.connect(
                        lambda _, fp=window.file_path: self._generate_file_report(fp)
                    )
                    widget.settings_button.clicked.connect(
                        lambda _, fp=window.file_path: self._show_file_settings(fp)
                    )
                    
                    # Set item size and add to list
                    item.setSizeHint(widget.sizeHint())
                    self.open_files_list.addItem(item)
                    self.open_files_list.setItemWidget(item, widget)
                    
                    if is_tracked:
                        item.setBackground(QColor(220, 237, 220))  # Soft green color
        
        # Remove items for files that are no longer open
        for file_path, (item, _) in current_items.items():
            if file_path not in current_files:
                row = self.open_files_list.row(item)
                self.open_files_list.takeItem(row)
        
    def _toggle_file_pause(self, file_path: str, is_paused: bool):
        """Toggle pause state for a specific file."""
        if file_path == self.tracked_file_path:
            self.is_paused = is_paused
            # Find the item by file path in user data
            for i in range(self.open_files_list.count()):
                item = self.open_files_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == file_path:
                    widget = self.open_files_list.itemWidget(item)
                    logger.info(f"{'Paused' if is_paused else 'Resumed'} tracking for file: {file_path}")
                    break
            self._update_open_files_list()

    def _update_file_rate(self, file_path: str, rate: float):
        """Update hourly rate for a specific file."""
        session = self.file_sessions.get(file_path)
        if session:
            old_rate = session.hourly_rate
            session.hourly_rate = rate
            logger.info(f"[SETTINGS] Rate changed for {file_path} - ${old_rate:.2f}/hr → ${rate:.2f}/hr")
            self._update_open_files_list()

    def _start_tracking_file(self, file_path: str):
        """Start tracking a specific file."""
        # Store current session if switching files
        if self.current_session and self.tracked_file_path:
            self.file_sessions[self.tracked_file_path] = self.current_session
            
        # Get or create session for the new file
        self.tracked_file_path = file_path
        if file_path in self.file_sessions:
            # Use existing session with its current rate
            self.current_session = self.file_sessions[file_path]
            logger.info(f"Resumed tracking file: {file_path} with rate: ${self.current_session.hourly_rate:.2f}")
        else:
            # Create new session with default rate
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            default_rate = self.settings.value("default_hourly_rate", 75.0, type=float)
            self.current_session = self.session_logger.start_session(
                project_id=file_name,
                file_path=file_path,
                hourly_rate=default_rate  # Use default rate only for new files
            )
            self.file_sessions[file_path] = self.current_session
            logger.info(f"Started tracking new file: {file_path} with default rate: ${default_rate:.2f}")
            
        # Update UI
        self._update_open_files_list()
        
        logger.info(f"Switched to tracking file: {file_path}")
        
    def _update_totals_display(self):
        """Update the project totals display."""
        self.totals_table.setRowCount(0)
        total_duration = timedelta()
        total_amount = 0.0
        
        # Group sessions by project ID to combine durations
        project_totals = {}
        
        for file_path, session in self.file_sessions.items():
            # Skip entries that are log messages
            if session.project_id.startswith("Opening File:"):
                continue
                
            # Get or create project total
            if session.project_id not in project_totals:
                project_totals[session.project_id] = {
                    'duration': timedelta(),
                    'amount': 0.0,
                    'rate': session.hourly_rate
                }
                
            # Add to project totals
            project_totals[session.project_id]['duration'] += session.active_duration
            project_totals[session.project_id]['amount'] += session.billable_amount
            
        # Add rows for each project
        for project_id, totals in project_totals.items():
            row = self.totals_table.rowCount()
            self.totals_table.insertRow(row)
            
            # Project name
            self.totals_table.setItem(row, 0, QTableWidgetItem(project_id))
            
            # Time
            duration = str(totals['duration']).split('.')[0]  # Remove microseconds
            self.totals_table.setItem(row, 1, QTableWidgetItem(duration))
            
            # Rate
            rate_item = QTableWidgetItem(f"${totals['rate']:.2f}")
            self.totals_table.setItem(row, 2, rate_item)
            
            # Amount
            amount_item = QTableWidgetItem(f"${totals['amount']:.2f}")
            self.totals_table.setItem(row, 3, amount_item)
            
            total_duration += totals['duration']
            total_amount += totals['amount']
        
        # Update grand totals
        total_hours = int(total_duration.total_seconds() // 3600)
        total_minutes = int((total_duration.total_seconds() % 3600) // 60)
        self.total_time_label.setText(f"Total Time: {total_hours:02d}:{total_minutes:02d}")
        self.total_amount_label.setText(f"Total Amount: ${total_amount:.2f}")

    def _update_status(self):
        """Update the status display."""
        current_time = datetime.now()
        
        # Check for Vectorworks windows
        windows = self.process_monitor.refresh()
        active_window = self.process_monitor.get_active_window()
        
        # Update open files list
        self._update_open_files_list()
        
        if windows:
            # Start tracking automatically when a file is detected
            if active_window and active_window.file_path:
                if not self.current_session:
                    self._start_tracking_file(active_window.file_path)
                elif self.auto_track_enabled and active_window.file_path != self.tracked_file_path:
                    self._start_tracking_file(active_window.file_path)
            
            # Update time tracking
            is_active = self.activity_monitor.is_active()
            is_tracking = False
            
            if active_window and active_window.file_path:
                if active_window.file_path == self.tracked_file_path:
                    is_tracking = True
                    
                    # Get the file widget to check its idle timeout setting
                    matching_items = self.open_files_list.findItems(active_window.file_path, Qt.MatchFlag.MatchExactly)
                    if matching_items:
                        file_widget = self.open_files_list.itemWidget(matching_items[0])
                        # Update activity monitor with file-specific idle timeout
                        self.activity_monitor.set_idle_timeout(file_widget.idle_timeout_minutes * 60)
                
            if is_active and is_tracking and self.current_session and not self.is_paused:
                time_diff = current_time - self.last_activity_check
                if time_diff.total_seconds() > 0:
                    self.session_logger.update_session_duration(self.current_session, time_diff)
                    logger.info(f"Added time: {time_diff.total_seconds():.2f} seconds")
        
        # Update totals display
        self._update_totals_display()
        
        self.last_activity_check = current_time
        
    def _on_activity_change(self, is_active: bool):
        """Handle activity state changes."""
        if not self.current_session:
            return
            
        logger.debug(f"Activity change callback - Active: {is_active}")
        
        # No need to update time here as it's handled in _update_status
        self.last_activity_check = datetime.now()
        
    def _generate_file_report(self, file_path: str):
        """Generate a PDF report for a specific file."""
        session = self.file_sessions.get(file_path)
        if not session:
            QMessageBox.warning(self, "No Data",
                              "No tracking data available for this file.")
            return
            
        # Create reports directory if it doesn't exist
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        report_path = reports_dir / f"{file_name}_report_{timestamp}.pdf"
        
        try:
            self._create_pdf_report(session, str(report_path))
            response = QMessageBox.information(
                self, "Report Generated",
                f"Report saved to: {report_path}\nOpen reports folder?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            # Open reports folder if user clicks Yes
            if response == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(reports_dir)))
        except Exception as e:
            QMessageBox.critical(self, "Error",
                               f"Failed to generate report: {e}")
            logger.error(f"Error generating report: {e}")

    def _create_pdf_report(self, session: TimeSession, output_path: str):
        """Create a detailed PDF report for a session."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        except ImportError:
            QMessageBox.warning(self, "Missing Dependency",
                              "Please install reportlab: pip install reportlab")
            return
            
        # Create the document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Content elements
        elements = []
        
        # Title
        elements.append(Paragraph("VectorTrack Time Report", title_style))
        elements.append(Spacer(1, 20))

        # File Information
        elements.append(Paragraph("File Information", heading_style))
        elements.append(Spacer(1, 10))

        file_info = [
            ["File Name:", os.path.basename(session.file_path)],
            ["Project ID:", session.project_id],
            ["First Opened:", session.start_time.strftime("%Y-%m-%d %H:%M:%S")],
            ["Last Active:", session.end_time.strftime("%Y-%m-%d %H:%M:%S") if session.end_time else "Currently Active"],
            ["Hourly Rate:", f"${session.hourly_rate:.2f}"],
        ]
        
        t = Table(file_info, colWidths=[1.5*inch, 4*inch])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

        # Session History
        elements.append(Paragraph("Session History", heading_style))
        elements.append(Spacer(1, 10))

        # Get all sessions for this file from the database
        all_sessions = self.session_logger.get_project_sessions(session.project_id)
        
        if all_sessions:
            session_data = [
                ["Start Time", "End Time", "Duration", "Amount"]
            ]
            
            for s in all_sessions:
                duration = str(s.active_duration).split('.')[0]  # Remove microseconds
                session_data.append([
                    s.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    s.end_time.strftime("%Y-%m-%d %H:%M:%S") if s.end_time else "Ongoing",
                    duration,
                    f"${s.billable_amount:.2f}"
                ])
            
            t = Table(session_data, colWidths=[1.5*inch, 1.5*inch, 1*inch, 1*inch])
            t.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 20))
            
        # Time Summary
        elements.append(Paragraph("Time Summary", heading_style))
        elements.append(Spacer(1, 10))
        
        total_duration = sum((s.active_duration for s in all_sessions), timedelta())
        total_billable = sum(s.billable_amount for s in all_sessions)
        total_hours = int(total_duration.total_seconds() // 3600)
        total_minutes = int((total_duration.total_seconds() % 3600) // 60)
        
        time_summary = [
            ["Total Sessions:", str(len(all_sessions))],
            ["Total Time:", f"{total_hours:02d}:{total_minutes:02d}"],
            ["Total Billable:", f"${total_billable:.2f}"],
        ]
        
        t = Table(time_summary, colWidths=[1.5*inch, 4*inch])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        
        # Build the PDF
        doc.build(elements)

    def _generate_report(self):
        """Generate a time tracking report for all files."""
        # Create reports directory if it doesn't exist
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"complete_report_{timestamp}.pdf"
        
        try:
            self._create_complete_pdf_report(str(report_path))
            response = QMessageBox.information(
                self, "Report Generated",
                f"Report saved to: {report_path}\nOpen reports folder?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            # Open reports folder if user clicks Yes
            if response == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(reports_dir)))
        except Exception as e:
            QMessageBox.critical(self, "Error",
                               f"Failed to generate report: {e}")
            logger.error(f"Error generating report: {e}")
            
    def _create_complete_pdf_report(self, output_path: str):
        """Create a complete PDF report for all tracked files."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
        except ImportError:
            QMessageBox.warning(self, "Missing Dependency",
                              "Please install reportlab: pip install reportlab")
            return
            
        # Create the document in portrait orientation
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Create a style for wrapped project names
        project_style = ParagraphStyle(
            'ProjectStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=12,
            wordWrap='CJK',
            alignment=1  # Center alignment
        )
        
        # Content elements
        elements = []
        
        # Title
        elements.append(Paragraph("VectorTrack Master Time Report", title_style))
        elements.append(Spacer(1, 20))

        # Report generation info
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        elements.append(Spacer(1, 20))
        
        # Project Summary
        elements.append(Paragraph("Project Summary", heading_style))
        elements.append(Spacer(1, 10))

        # Collect all unique projects
        all_projects = {}
        for file_path, session in self.file_sessions.items():
            project_id = session.project_id
            if project_id not in all_projects:
                all_projects[project_id] = {
                    'files': [],
                    'total_time': timedelta(),
                    'total_billable': 0.0,
                    'sessions': []
                }
            all_projects[project_id]['files'].append(file_path)
            
            # Get all sessions for this project
            project_sessions = self.session_logger.get_project_sessions(project_id)
            all_projects[project_id]['sessions'].extend(project_sessions)
            all_projects[project_id]['total_time'] = sum((s.active_duration for s in project_sessions), timedelta())
            all_projects[project_id]['total_billable'] = sum(s.billable_amount for s in project_sessions)

        # Create project summary table with wrapped project names
        summary_data = [
            ["Project", "Files", "Total Time", "Sessions", "Billable"]
        ]

        grand_total_time = timedelta()
        grand_total_billable = 0.0
        grand_total_sessions = 0

        for project_id, data in all_projects.items():
            total_hours = int(data['total_time'].total_seconds() // 3600)
            total_minutes = int((data['total_time'].total_seconds() % 3600) // 60)
            # Wrap project name in Paragraph for automatic wrapping
            summary_data.append([
                Paragraph(project_id, project_style),
                len(data['files']),
                f"{total_hours:02d}:{total_minutes:02d}",
                len(data['sessions']),
                f"${data['total_billable']:.2f}"
            ])
            grand_total_time += data['total_time']
            grand_total_billable += data['total_billable']
            grand_total_sessions += len(data['sessions'])

        # Add grand totals
        grand_total_hours = int(grand_total_time.total_seconds() // 3600)
        grand_total_minutes = int((grand_total_time.total_seconds() % 3600) // 60)
        summary_data.append([
            Paragraph("GRAND TOTAL", project_style),
            sum(len(d['files']) for d in all_projects.values()),
            f"{grand_total_hours:02d}:{grand_total_minutes:02d}",
            grand_total_sessions,
            f"${grand_total_billable:.2f}"
        ])

        # Create and style the summary table with adjusted column widths
        available_width = doc.width
        t = Table(summary_data, colWidths=[
            available_width * 0.35,  # Project column (35% of width)
            available_width * 0.10,  # Files column
            available_width * 0.20,  # Total Time column
            available_width * 0.15,  # Sessions column
            available_width * 0.20   # Billable column
        ])
        t.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),  # Center all columns except project names
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically center all cells
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ROWHEIGHT', (0, 0), (-1, -1), 30),  # Minimum row height for wrapped text
        ]))
        elements.append(t)
        elements.append(Spacer(1, 30))

        # Detailed Project Information
        for project_id, data in all_projects.items():
            project_section = []
            project_section.append(Paragraph(f"Project: {project_id}", heading_style))
            project_section.append(Spacer(1, 10))

            # File list
            project_section.append(Paragraph("Files:", normal_style))
            for file_path in data['files']:
                project_section.append(Paragraph(f"• {os.path.basename(file_path)}", normal_style))
            project_section.append(Spacer(1, 10))

            # Session history
            project_section.append(Paragraph("Session History:", normal_style))
            project_section.append(Spacer(1, 5))

            session_data = [
                ["Start Time", "End Time", "Duration", "Rate", "Amount"]
            ]

            for s in sorted(data['sessions'], key=lambda x: x.start_time):
                duration = str(s.active_duration).split('.')[0]  # Remove microseconds
                session_data.append([
                    s.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    s.end_time.strftime("%Y-%m-%d %H:%M:%S") if s.end_time else "Ongoing",
                    duration,
                    f"${s.hourly_rate:.2f}",
                    f"${s.billable_amount:.2f}"
                ])

            # Adjust session table column widths for portrait mode
            t = Table(session_data, colWidths=[
                available_width * 0.25,  # Start Time
                available_width * 0.25,  # End Time
                available_width * 0.20,  # Duration
                available_width * 0.15,  # Rate
                available_width * 0.15   # Amount
            ])
            t.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            project_section.append(t)
            project_section.append(Spacer(1, 30))
            
            # Keep each project section together if possible
            elements.append(KeepTogether(project_section))

        # Build the PDF
        doc.build(elements)

    def closeEvent(self, event):
        """Handle application shutdown."""
        if self.current_session:
            self.session_logger.end_session(self.current_session)
        self.activity_monitor.stop()
        event.accept()

    def _show_session_log(self, file_path: str):
        """Show the session log dialog for a file."""
        session = self.file_sessions.get(file_path)
        dialog = SessionLogDialog(file_path, session, self)
        dialog.exec()

    def _show_file_settings(self, file_path: str):
        """Show settings dialog for a specific file."""
        # TODO: Implement file-specific settings dialog
        pass

    def _show_settings_dialog(self):
        """Show the application settings dialog."""
        dialog = ApplicationSettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.get_settings()
            
            # Update settings
            self.settings.setValue("default_hourly_rate", settings['default_hourly_rate'])
            self.settings.setValue("default_idle_timeout", settings['default_idle_timeout'])
            self.settings.setValue("auto_track_enabled", settings['auto_track_enabled'])
            
            # Update application state
            self.auto_track_enabled = settings['auto_track_enabled']
            self.auto_track_checkbox.setChecked(settings['auto_track_enabled'])
            
            logger.info("Application settings updated")
            logger.info(f"Default rate: ${settings['default_hourly_rate']:.2f}/hr")
            logger.info(f"Default idle timeout: {settings['default_idle_timeout']} minutes")
            logger.info(f"Auto-track enabled: {settings['auto_track_enabled']}")

def main():
    """Main entry point for the application."""
    try:
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Configure logging with rotation and cleanup
        logger.add(
            "logs/vectortrack.log",  # Use a single log file
            rotation="1 day",        # Create new file daily
            retention="7 days",      # Keep logs for 7 days
            compression="zip",       # Compress old logs
            enqueue=True,           # Thread-safe logging
            backtrace=True,         # Detailed error logs
            diagnose=True,          # Include variable values in errors
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
        
        logger.info(f"Starting VectorTrack v{__version__}")
        logger.info(f"Python version: {platform.python_version()}")
        logger.info(f"Operating system: {platform.system()} {platform.version()}")
        logger.info(f"Qt version: {QApplication.applicationVersion()}")
        
        # Start application
        app = QApplication(sys.argv)
        logger.info("QApplication initialized")
        
        window = MainWindow()
        logger.info("Main window created")
        
        window.show()
        logger.info("Main window displayed")
        
        exit_code = app.exec()
        logger.info(f"Application exiting with code: {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.exception("Fatal error during application startup")
        sys.exit(1)