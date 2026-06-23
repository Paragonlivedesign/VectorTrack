"""Cross-machine Vectorworks log sync via a cloud-synced folder."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Optional, Tuple

from vectortrack.log_parser import LOG_FILENAME, read_log_content
from vectortrack.sync_config import SyncConfig

MACHINES_SUBDIR = "machines"
SYNC_META_FILENAME = "sync_meta.json"


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

        meta = {
            "last_push_time": datetime.now().isoformat(timespec="seconds"),
            "source_path": local_log_path,
            "byte_size": os.path.getsize(dest_path),
            "machine_id": machine_id,
            "machine_label": sync_config.machine_label,
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

    if sync_config.sync_on_refresh and local_log_paths:
        push_log_snapshot(local_log_paths[0], sync_config, vw_year)

    remote_paths = discover_remote_log_paths(sync_folder, sync_config.machine_id, vw_year)
    for remote_path in remote_paths:
        if remote_path not in paths:
            paths.append(remote_path)

    machine_count = 1 + len(remote_paths)
    return paths, machine_count
