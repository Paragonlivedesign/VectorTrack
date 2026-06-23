"""Configuration values and storage path helpers for VectorTrack 0.5."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

APP_NAME = "VectorTrack"
APP_VERSION = "0.5.0"
APP_BETA = True


def format_version(*, include_product_name: bool = False) -> str:
    """Return semver label, with optional product name and beta suffix."""
    label = f"{APP_NAME} {APP_VERSION}" if include_product_name else APP_VERSION
    if APP_BETA:
        label += " beta"
    return label

ENFORCE_LICENSING = False

PARAGON_VENDOR = "Paragon"
PARAGON_VENDOR_DIR = "Paragon"
PARAGON_PRODUCT_DIR = "VectorTrack"
COMPANY_NAME = "Paragon Live Design"
SUPPORT_EMAIL = "Info@paragonlivedesign.com"
VENMO_HANDLE = "@Cody-Lisle"
DONATE_MESSAGE = "Love VectorTrack? Support development on Venmo."

DEFAULT_DB_FILENAME = "vectortrack.db"
LEGACY_DB_FILENAME = "sessions.db"

DEFAULT_HOURLY_RATE = 75.0
DEFAULT_IDLE_MINUTES = 5
DEFAULT_ROUNDING_MINUTES = 15
BUDGET_WARN_PERCENT = 0.8
LOG_SYNC_INTERVAL_SEC = 60
AUTO_SAVE_INTERVAL_SEC = 30
BACKUP_RETENTION_COUNT = 10

ENV_DATA_DIR = "VECTORTRACK_DATA_DIR"

_portable_mode = False


def set_portable_mode(enabled: bool) -> None:
    """Enable or disable portable mode data storage."""
    global _portable_mode
    _portable_mode = bool(enabled)


def _exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resolve_data_dir() -> Path:
    """Resolve and create the writable application data directory."""
    if _portable_mode:
        data_dir = _exe_dir() / "data"
    else:
        override = os.getenv(ENV_DATA_DIR)
        if override:
            data_dir = Path(override).expanduser()
        elif sys.platform.startswith("win"):
            base = Path(os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or Path.home())
            data_dir = base / PARAGON_VENDOR_DIR / PARAGON_PRODUCT_DIR
        else:
            data_dir = Path.home() / ".local" / "share" / APP_NAME.lower()

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def db_path() -> Path:
    """Full path to the v4 SQLite database file."""
    return resolve_data_dir() / DEFAULT_DB_FILENAME


def legacy_db_path() -> Path:
    """Full path to the v1 legacy sessions database."""
    return resolve_data_dir() / LEGACY_DB_FILENAME


def paths_json_path() -> Path:
    """Full path to runtime paths metadata file."""
    return resolve_data_dir() / "paths.json"


def projects_json_path() -> Path:
    """Full path to legacy-style project mapping file."""
    return resolve_data_dir() / "projects.json"


def log_library_path() -> Path:
    """Full path to log library cache file."""
    return resolve_data_dir() / "log_library.json"


def license_file_path() -> Path:
    """Full path to encrypted license data file."""
    return resolve_data_dir() / "license.json"


def license_key_path() -> Path:
    """Full path to license encryption key file."""
    return resolve_data_dir() / "key.dat"


def read_paths_json() -> dict[str, Any]:
    """Load existing paths.json payload, or return an empty dict."""
    target = paths_json_path()
    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return {}


def write_paths_json(extra: dict[str, Any] | None = None) -> Path:
    """Write a small path manifest consumed by legacy tooling."""
    payload = read_paths_json()
    payload.update(
        {
            "portable_mode": _portable_mode,
            "data_dir": str(resolve_data_dir()),
            "db_path": str(db_path()),
            "legacy_db_path": str(legacy_db_path()),
            "projects_json": str(projects_json_path()),
            "log_library": str(log_library_path()),
        }
    )
    if extra:
        payload.update(extra)
    target = paths_json_path()
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target
