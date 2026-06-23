"""
VectorTrackScript 0.5 configuration helpers (paths.json + project metadata).
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

PLUGIN_FOLDER = "VectorTrackScript 0.5"
PATHS_FILENAME = "paths.json"


@dataclass(frozen=True)
class SyncConfig:
    enabled: bool = False
    folder: str = ""
    machine_id: str = ""
    machine_label: str = ""
    sync_on_refresh: bool = True


def default_machine_id() -> str:
    hostname = socket.gethostname() or "unknown"
    return hashlib.sha256(hostname.encode("utf-8")).hexdigest()[:16]


def load_sync_config(vw_year: int, plugin_folder: str = PLUGIN_FOLDER) -> SyncConfig:
    payload = load_paths_json(vw_year, plugin_folder)
    raw = payload.get("sync")
    if not isinstance(raw, dict):
        return SyncConfig()

    enabled = bool(raw.get("enabled", False))
    folder = raw.get("folder")
    machine_id = raw.get("machine_id")
    machine_label = raw.get("machine_label")
    sync_on_refresh = raw.get("sync_on_refresh", True)

    resolved_folder = ""
    if isinstance(folder, str) and folder.strip():
        resolved_folder = os.path.expandvars(os.path.expanduser(folder.strip()))

    resolved_machine_id = ""
    if isinstance(machine_id, str) and machine_id.strip():
        resolved_machine_id = machine_id.strip()
    else:
        resolved_machine_id = default_machine_id()

    resolved_label = ""
    if isinstance(machine_label, str):
        resolved_label = machine_label.strip()

    return SyncConfig(
        enabled=enabled,
        folder=resolved_folder,
        machine_id=resolved_machine_id,
        machine_label=resolved_label,
        sync_on_refresh=bool(sync_on_refresh),
    )


def sync_config_to_dict(sync_config: SyncConfig) -> Dict[str, Any]:
    return {
        "enabled": sync_config.enabled,
        "folder": sync_config.folder,
        "machine_id": sync_config.machine_id or default_machine_id(),
        "machine_label": sync_config.machine_label,
        "sync_on_refresh": sync_config.sync_on_refresh,
    }


def save_sync_config(
    vw_year: int,
    sync_config: SyncConfig,
    plugin_folder: str = PLUGIN_FOLDER,
) -> str:
    """Persist sync settings into paths.json. Returns the written file path."""
    payload = load_paths_json(vw_year, plugin_folder)
    if sync_config.enabled or sync_config.folder.strip():
        payload["sync"] = sync_config_to_dict(sync_config)
    else:
        payload.pop("sync", None)

    path = paths_json_path(vw_year, plugin_folder)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return path


def _normalize_name(name: str) -> str:
    return os.path.basename((name or "").replace("\\", "/")).strip().lower()


def plugin_data_dir_for_year(vw_year: int, plugin_folder: str = PLUGIN_FOLDER) -> str:
    return os.path.join(
        os.path.expanduser("~"),
        "AppData",
        "Roaming",
        "Nemetschek",
        "Vectorworks",
        str(vw_year),
        "Plug-ins",
        plugin_folder,
    )


def paths_json_path(vw_year: int, plugin_folder: str = PLUGIN_FOLDER) -> str:
    return os.path.join(plugin_data_dir_for_year(vw_year, plugin_folder), PATHS_FILENAME)


def load_paths_json(vw_year: int, plugin_folder: str = PLUGIN_FOLDER) -> Dict[str, Any]:
    path = paths_json_path(vw_year, plugin_folder)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            return payload
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return {}


def resolve_plugin_data_dir(vw_year: int, plugin_folder: str = PLUGIN_FOLDER) -> str:
    fallback = plugin_data_dir_for_year(vw_year, plugin_folder)
    payload = load_paths_json(vw_year, plugin_folder)
    configured = payload.get("plugin_data_dir") or payload.get("data_dir")
    if isinstance(configured, str) and configured.strip():
        return os.path.expandvars(os.path.expanduser(configured.strip()))
    return fallback


def aliases_from_paths(vw_year: int, plugin_folder: str = PLUGIN_FOLDER) -> Dict[str, list[str]]:
    payload = load_paths_json(vw_year, plugin_folder)
    out: Dict[str, list[str]] = {}
    for key in ("aliases", "project_aliases"):
        raw = payload.get(key)
        if not isinstance(raw, dict):
            continue
        for canonical, aliases in raw.items():
            if not isinstance(canonical, str):
                continue
            values: Iterable[Any]
            if isinstance(aliases, list):
                values = aliases
            elif isinstance(aliases, str):
                values = [aliases]
            else:
                continue
            cleaned = [str(item).strip() for item in values if str(item).strip()]
            if cleaned:
                out[canonical] = cleaned
    return out


def project_details_from_paths(
    vw_year: int,
    project_name: str,
    plugin_folder: str = PLUGIN_FOLDER,
) -> Dict[str, Any]:
    payload = load_paths_json(vw_year, plugin_folder)
    projects = payload.get("projects")
    if not isinstance(projects, dict):
        return {}

    normalized_target = _normalize_name(project_name)
    for project_key, details in projects.items():
        if not isinstance(details, dict):
            continue
        names = [project_key]
        aliases = details.get("aliases")
        if isinstance(aliases, list):
            names.extend(str(alias) for alias in aliases)
        elif isinstance(aliases, str):
            names.append(aliases)

        if any(_normalize_name(name) == normalized_target for name in names):
            return details
    return {}

