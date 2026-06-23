"""Cross-machine log sync configuration for VectorTrack 0.5."""

from __future__ import annotations

import hashlib
import json
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SyncConfig:
    enabled: bool = False
    folder: str = ""
    machine_id: str = ""
    machine_label: str = ""
    sync_on_refresh: bool = True


def default_machine_id() -> str:
    hostname = socket.gethostname() or "unknown"
    return hashlib.sha256(hostname.encode("utf-8")).hexdigest()[:16]


def sync_config_from_mapping(raw: dict[str, Any] | None) -> SyncConfig:
    if not isinstance(raw, dict):
        return SyncConfig()

    folder = raw.get("folder")
    machine_id = raw.get("machine_id")
    machine_label = raw.get("machine_label")

    resolved_folder = ""
    if isinstance(folder, str) and folder.strip():
        resolved_folder = str(Path(folder.strip()).expanduser())

    resolved_machine_id = ""
    if isinstance(machine_id, str) and machine_id.strip():
        resolved_machine_id = machine_id.strip()
    else:
        resolved_machine_id = default_machine_id()

    resolved_label = ""
    if isinstance(machine_label, str):
        resolved_label = machine_label.strip()

    return SyncConfig(
        enabled=bool(raw.get("enabled", False)),
        folder=resolved_folder,
        machine_id=resolved_machine_id,
        machine_label=resolved_label,
        sync_on_refresh=bool(raw.get("sync_on_refresh", True)),
    )


def sync_config_to_mapping(sync_config: SyncConfig) -> dict[str, Any]:
    return {
        "enabled": sync_config.enabled,
        "folder": sync_config.folder,
        "machine_id": sync_config.machine_id or default_machine_id(),
        "machine_label": sync_config.machine_label,
        "sync_on_refresh": sync_config.sync_on_refresh,
    }


def load_sync_config_from_paths_json(paths_file: Path) -> SyncConfig:
    if not paths_file.is_file():
        return SyncConfig()
    try:
        payload = json.loads(paths_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return SyncConfig()
    if not isinstance(payload, dict):
        return SyncConfig()
    raw = payload.get("sync")
    return sync_config_from_mapping(raw if isinstance(raw, dict) else None)


def load_sync_config_from_settings(
    *,
    enabled: bool = False,
    folder: str = "",
    machine_id: str = "",
    machine_label: str = "",
    sync_on_refresh: bool = True,
) -> SyncConfig:
    return SyncConfig(
        enabled=enabled,
        folder=folder,
        machine_id=machine_id or default_machine_id(),
        machine_label=machine_label,
        sync_on_refresh=sync_on_refresh,
    )


def settings_keys_from_sync_config(sync_config: SyncConfig) -> dict[str, object]:
    return {
        "sync_enabled": sync_config.enabled,
        "sync_folder": sync_config.folder,
        "sync_machine_id": sync_config.machine_id or default_machine_id(),
        "sync_machine_label": sync_config.machine_label,
        "sync_on_refresh": sync_config.sync_on_refresh,
    }
