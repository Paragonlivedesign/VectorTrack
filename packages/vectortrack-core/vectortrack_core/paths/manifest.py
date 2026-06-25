"""paths.json manifest helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vectortrack_core.constants import DEFAULT_HOURLY_RATE
from vectortrack_core.sync.config import SyncConfig, sync_config_to_mapping


def read_paths_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return {}


def write_paths_json(
    path: Path,
    *,
    portable_mode: bool,
    data_dir: Path,
    db_path: Path,
    legacy_db_path: Path,
    sync_config: SyncConfig | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    payload = read_paths_json(path)
    payload.update(
        {
            "portable_mode": portable_mode,
            "data_dir": str(data_dir),
            "db_path": str(db_path),
            "legacy_db_path": str(legacy_db_path),
            "default_hourly_rate": DEFAULT_HOURLY_RATE,
        }
    )
    if sync_config is not None:
        payload["sync"] = sync_config_to_mapping(sync_config)
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def default_hourly_rate_from_paths(path: Path) -> float:
    payload = read_paths_json(path)
    raw = payload.get("default_hourly_rate")
    try:
        if raw is not None:
            return float(raw)
    except (TypeError, ValueError):
        pass
    return DEFAULT_HOURLY_RATE
