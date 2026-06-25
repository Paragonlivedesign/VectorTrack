"""
Cross-machine Vectorworks log sync via a cloud-synced folder (no OAuth required).
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

from vectortrack_config import SyncConfig
from vectortrack_log import LOG_FILENAME, read_log_content

try:
    from vectortrack_core.sync.folder import (
        discover_remote_log_paths,
        push_log_snapshot,
        resolve_sync_folder,
        snapshot_dir,
        snapshot_path,
    )
except ImportError:
    from datetime import datetime
    import json

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

    def push_log_snapshot(local_log_path, sync_config, vw_year):
        sync_folder = resolve_sync_folder(sync_config)
        if not sync_folder:
            return False, "Sync not configured"
        dest_dir = snapshot_dir(sync_folder, sync_config.machine_id, vw_year)
        dest_path = os.path.join(dest_dir, LOG_FILENAME)
        try:
            os.makedirs(dest_dir, exist_ok=True)
            with open(local_log_path, encoding="utf-8", errors="replace") as src:
                content = src.read()
            with open(dest_path, "w", encoding="utf-8") as dst:
                dst.write(content)
            meta = {
                "last_push_time": datetime.now().isoformat(timespec="seconds"),
                "machine_id": sync_config.machine_id,
            }
            with open(os.path.join(dest_dir, SYNC_META_FILENAME), "w", encoding="utf-8") as handle:
                json.dump(meta, handle, indent=2)
            return True, ""
        except OSError as exc:
            return False, str(exc)

    def discover_remote_log_paths(sync_folder, machine_id, vw_year):
        machines_dir = os.path.join(sync_folder, MACHINES_SUBDIR)
        if not os.path.isdir(machines_dir):
            return []
        paths = []
        for entry in os.scandir(machines_dir):
            if not entry.is_dir() or entry.name == machine_id:
                continue
            candidate = os.path.join(entry.path, str(vw_year), LOG_FILENAME)
            if os.path.isfile(candidate):
                paths.append(candidate)
        return sorted(paths)


def gather_log_sources_for_sync(
    local_log_path: str,
    sync_config: SyncConfig,
    vw_year: int,
) -> Tuple[List[str], int, Optional[str]]:
    """
    Collect local and remote log contents for merged parsing.

    Returns (sources, machine_count, status_note).
    """
    try:
        sources = [read_log_content(local_log_path)]
    except OSError as exc:
        return [], 0, f"Error reading local log: {exc}"

    if not sync_config.enabled:
        return sources, 1, None

    sync_folder = resolve_sync_folder(sync_config)
    if not sync_folder:
        return sources, 1, None

    if not os.path.isdir(sync_folder):
        return sources, 1, "Sync folder unavailable — local log only"

    if sync_config.sync_on_refresh:
        push_log_snapshot(local_log_path, sync_config, vw_year)

    remote_paths = discover_remote_log_paths(sync_folder, sync_config.machine_id, vw_year)
    for remote_path in remote_paths:
        try:
            sources.append(read_log_content(remote_path))
        except OSError:
            continue

    machine_count = 1 + len(remote_paths)
    return sources, machine_count, None
