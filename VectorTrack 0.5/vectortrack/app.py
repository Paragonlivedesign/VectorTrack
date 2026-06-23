"""Application bootstrap for VectorTrack 0.5."""

from __future__ import annotations

import argparse
import platform
import sqlite3
import sys

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication
from loguru import logger

from vectortrack import __version__, config
from vectortrack.activity_monitor import ActivityMonitor
from vectortrack.db.repository import Repository
from vectortrack.db.schema import migrate
from vectortrack.process_monitor import ProcessMonitor
from vectortrack.services.backup_service import BackupService
from vectortrack.services.billing_service import BillingService
from vectortrack.services.log_service import LogService
from vectortrack.services.tracking_service import TrackingService
from vectortrack.single_instance import SingleInstanceGuard
from vectortrack.ui import MainWindow, apply_theme
from vectortrack.ui.app_icon import app_icon
from vectortrack.ui.dialogs.about_dialog import AboutDialog
from vectortrack.ui.dialogs.donate_dialog import DonateDialog
from vectortrack.ui.dialogs.manual_entry_dialog import ManualEntryDialog
from vectortrack.ui.dialogs.project_assign_dialog import ProjectAssignDialog
from vectortrack.ui.dialogs.project_editor_dialog import ProjectEditorDialog
from vectortrack.ui.dialogs.settings_dialog import SettingsDialog

__all__ = [
    "AboutDialog",
    "DonateDialog",
    "ManualEntryDialog",
    "ProjectAssignDialog",
    "ProjectEditorDialog",
    "SettingsDialog",
    "MainWindow",
    "main",
]


def _configure_logging() -> None:
    logs_dir = config.logs_dir()
    logger.remove()
    logger.add(
        str(logs_dir / "vectortrack.log"),
        rotation="1 day",
        retention="7 days",
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=True,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )


def _init_services() -> MainWindow:
    data_dir = config.resolve_data_dir()
    db_file = data_dir / config.DEFAULT_DB_FILENAME
    legacy_file = data_dir / config.LEGACY_DB_FILENAME
    with sqlite3.connect(str(db_file)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        migrate(conn, legacy_db_file=legacy_file)
        conn.commit()

    repository = Repository(database_path=db_file, legacy_database_path=legacy_file)
    process_monitor = ProcessMonitor()
    idle_seconds = int(
        QApplication.instance().property("vectortrack_idle_seconds")
        or (config.DEFAULT_IDLE_MINUTES * 60)
    )
    activity_monitor = ActivityMonitor(idle_timeout_seconds=idle_seconds)
    tracking_service = TrackingService(
        process_monitor=process_monitor,
        activity_monitor=activity_monitor,
        repository=repository,
        autosave_seconds=config.AUTO_SAVE_INTERVAL_SEC,
    )
    window = MainWindow(
        repository=repository,
        tracking_service=tracking_service,
        log_service=LogService(),
        billing_service=BillingService(),
        process_monitor=process_monitor,
        activity_monitor=activity_monitor,
    )
    config.write_paths_json()
    return window


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="vectortrack")
    parser.add_argument(
        "--portable",
        action="store_true",
        help="Store app data in ./data next to executable.",
    )
    return parser.parse_args(argv)


def _backup_on_exit() -> None:
    data_dir = config.resolve_data_dir()
    backup_service = BackupService(
        backup_dir=str(data_dir / "backups"),
        retention_count=config.BACKUP_RETENTION_COUNT,
    )
    backup_service.create_backup(
        paths=[
            str(config.db_path()),
            str(config.paths_json_path()),
            str(config.projects_json_path()),
            str(config.log_library_path()),
        ],
        label="vectortrack_exit",
    )


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    config.set_portable_mode(args.portable)
    _configure_logging()
    logger.info(f"Starting VectorTrack v{__version__}")
    logger.info(f"Python {platform.python_version()} on {platform.system()} {platform.version()}")
    logger.info(f"Data directory: {config.resolve_data_dir()}")
    if hasattr(QApplication, "setHighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())
    instance_guard = SingleInstanceGuard()
    if not instance_guard.acquire():
        logger.info("Another VectorTrack instance is already running; raising existing window")
        SingleInstanceGuard.notify_existing()
        sys.exit(0)
    mode = "dark" if config.ENFORCE_LICENSING and False else "light"
    apply_theme(app, mode=mode)
    window = _init_services()

    def _raise_existing_window() -> None:
        window.showNormal()
        window.raise_()
        window.activateWindow()
        QTimer.singleShot(0, window._ensure_window_on_screen)

    instance_guard.listen(_raise_existing_window)
    window.showNormal()
    window.raise_()
    window.activateWindow()
    QTimer.singleShot(0, window._ensure_window_on_screen)
    exit_code = 0
    try:
        exit_code = app.exec()
    finally:
        try:
            _backup_on_exit()
        except Exception as exc:  # pragma: no cover - backup should not block app exit
            logger.warning(f"Exit backup failed: {exc}")
    logger.info(f"Application exited: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

