"""Cross-machine Vectorworks log sync via a cloud-synced folder."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from vectortrack.log_parser import LOG_FILENAME, read_log_content
from vectortrack.services.vw_identity import resolve_sync_machine_label, resolve_vw_identity
from vectortrack.sync_config import SyncConfig

MACHINES_SUBDIR = "machines"
SYNC_META_FILENAME = "sync_meta.json"
ASSIGNMENTS_FILENAME = "assignments.json"


def resolve_sync_folder(sync_config: SyncConfig) -> Optional[str]:
    if not sync_config.enabled or not sync_config.folder:
        return None
    folder = sync_config.folder.strip()
    return folder if folder else None


def snapshot_dir(sync_folder: str, machine_id: str, vw_year: int) -> str:
    return os.path.join(sync_folder, MACHINES_SUBDIR, machine_id, str(vw_year))


def snapshot_path(sync_folder: str, machine_id: str, vw_year: int) -> str:
    return os.path.join(snapshot_dir(sync_folder, machine_id, vw_year), LOG_FILENAME)


def _atomic_write_text(path: str, content: str) -> None:
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        handle.write(content)
    os.replace(temp_path, path)


def _atomic_write_json(path: str, payload: dict) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2))


def push_log_snapshot(
    local_log_path: str,
    sync_config: SyncConfig,
    vw_year: int,
) -> Tuple[bool, str]:
    sync_folder = resolve_sync_folder(sync_config)
    if not sync_folder:
        return False, "Sync not configured"

    machine_id = sync_config.machine_id
    dest_dir = snapshot_dir(sync_folder, machine_id, vw_year)
    dest_path = os.path.join(dest_dir, LOG_FILENAME)

    try:
        os.makedirs(dest_dir, exist_ok=True)
        content = read_log_content(local_log_path)
        _atomic_write_text(dest_path, content)

        identity = resolve_vw_identity(vw_year)
        meta = {
            "last_push_time": datetime.now().isoformat(timespec="seconds"),
            "source_path": local_log_path,
            "byte_size": os.path.getsize(dest_path),
            "machine_id": machine_id,
            "machine_label": sync_config.machine_label,
            "machine_uuid": identity.machine_uuid,
            "license_id": identity.license_id,
        }
        _atomic_write_json(os.path.join(dest_dir, SYNC_META_FILENAME), meta)
        return True, ""
    except OSError as exc:
        return False, str(exc)


def discover_remote_log_paths(
    sync_folder: str,
    machine_id: str,
    vw_year: int,
) -> List[str]:
    machines_dir = os.path.join(sync_folder, MACHINES_SUBDIR)
    if not os.path.isdir(machines_dir):
        return []

    paths: List[str] = []
    for entry in os.scandir(machines_dir):
        if not entry.is_dir() or entry.name == machine_id:
            continue
        candidate = os.path.join(entry.path, str(vw_year), LOG_FILENAME)
        if os.path.isfile(candidate):
            paths.append(candidate)
    return sorted(paths)


def gather_sync_log_paths(
    local_log_paths: List[str],
    sync_config: SyncConfig,
    vw_year: int,
) -> Tuple[List[str], int]:
    """Return local + remote log paths for merged parsing."""
    paths = list(local_log_paths)
    if not sync_config.enabled:
        return paths, 1

    sync_folder = resolve_sync_folder(sync_config)
    if not sync_folder or not os.path.isdir(sync_folder):
        return paths, 1

    remote_paths = discover_remote_log_paths(sync_folder, sync_config.machine_id, vw_year)
    for remote_path in remote_paths:
        if remote_path not in paths:
            paths.append(remote_path)

    machine_count = 1 + len(remote_paths)
    return paths, machine_count


def assignments_path(sync_folder: str, machine_id: str, vw_year: int) -> str:
    return os.path.join(snapshot_dir(sync_folder, machine_id, vw_year), ASSIGNMENTS_FILENAME)


def _read_json_file(path: str) -> dict:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return {}


def _parse_updated_at(raw: object) -> datetime:
    if not raw:
        return datetime.min
    try:
        return datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return datetime.min


def _assignment_entries(payload: dict) -> dict[str, str]:
    nested = payload.get("assignments")
    if isinstance(nested, dict):
        source = nested
    else:
        source = payload
    entries: dict[str, str] = {}
    for key, value in source.items():
        if key in {"updated_at", "license_id", "assignments"}:
            continue
        code = str(value or "").strip()
        if code:
            entries[str(key)] = code
    return entries


def discover_assignment_paths(sync_folder: str, vw_year: int) -> List[Tuple[str, str]]:
    machines_dir = os.path.join(sync_folder, MACHINES_SUBDIR)
    if not os.path.isdir(machines_dir):
        return []

    discovered: List[Tuple[str, str]] = []
    for entry in os.scandir(machines_dir):
        if not entry.is_dir():
            continue
        year_path = os.path.join(entry.path, str(vw_year), ASSIGNMENTS_FILENAME)
        root_path = os.path.join(entry.path, ASSIGNMENTS_FILENAME)
        if os.path.isfile(year_path):
            discovered.append((entry.name, year_path))
        elif os.path.isfile(root_path):
            discovered.append((entry.name, root_path))
    return sorted(discovered)


def merge_remote_assignments(
    sync_folder: str,
    vw_year: int,
    local_assignments: dict[str, str],
    *,
    local_machine_id: str = "",
) -> dict[str, str]:
    """Merge basename → project_code assignments from all machines; local wins on tie."""
    merged: dict[str, Tuple[datetime, str, str]] = {}

    for machine_id, path in discover_assignment_paths(sync_folder, vw_year):
        payload = _read_json_file(path)
        updated = _parse_updated_at(payload.get("updated_at"))
        for basename, code in _assignment_entries(payload).items():
            key = os.path.basename(basename.replace("\\", "/"))
            existing = merged.get(key)
            if existing is None or updated > existing[0]:
                merged[key] = (updated, code, machine_id)

    local_updated = datetime.now()
    for file_path, code in local_assignments.items():
        if not code:
            continue
        key = os.path.basename(str(file_path).replace("\\", "/"))
        merged[key] = (local_updated, str(code).strip(), local_machine_id)

    return {basename: code for basename, (_updated, code, _machine) in merged.items()}


def push_assignments_snapshot(
    local_assignments: dict[str, str],
    sync_config: SyncConfig,
    vw_year: int,
) -> Tuple[bool, str]:
    sync_folder = resolve_sync_folder(sync_config)
    if not sync_folder:
        return False, "Sync not configured"

    machine_id = sync_config.machine_id
    dest_path = assignments_path(sync_folder, machine_id, vw_year)

    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        identity = resolve_vw_identity(vw_year)
        payload = {
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "license_id": identity.license_id,
            "assignments": {
                os.path.basename(str(path).replace("\\", "/")): str(code).strip()
                for path, code in local_assignments.items()
                if path and code
            },
        }
        _atomic_write_json(dest_path, payload)
        return True, ""
    except OSError as exc:
        return False, str(exc)


def load_sync_machine_labels(sync_folder: str, vw_year: int) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    machines_dir = os.path.join(sync_folder, MACHINES_SUBDIR)
    if not os.path.isdir(machines_dir):
        return labels

    for entry in os.scandir(machines_dir):
        if not entry.is_dir():
            continue
        meta_path = os.path.join(entry.path, str(vw_year), SYNC_META_FILENAME)
        if not os.path.isfile(meta_path):
            continue
        meta = _read_json_file(meta_path)
        label = str(meta.get("machine_label") or "").strip()
        if not label:
            license_id = str(meta.get("license_id") or "").strip()
            label = license_id or entry.name[:8]
        labels[entry.name] = label
    return labels


def resolve_machine_display(
    machine_id: str,
    *,
    sync_folder: str | None,
    vw_year: int,
    local_config: SyncConfig,
    label_cache: Dict[str, str] | None = None,
) -> str:
    value = (machine_id or "").strip()
    if not value:
        return resolve_sync_machine_label(local_config.machine_label, vw_year)

    if value == local_config.machine_id:
        return resolve_sync_machine_label(local_config.machine_label, vw_year)

    if label_cache is not None and value in label_cache:
        return label_cache[value]

    if sync_folder and os.path.isdir(sync_folder):
        labels = label_cache if label_cache is not None else load_sync_machine_labels(sync_folder, vw_year)
        cached = labels.get(value)
        if cached:
            return cached

    if len(value) > 12:
        return f"{value[:8]}…"
    return value
