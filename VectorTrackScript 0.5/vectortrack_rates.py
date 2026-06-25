"""
Per-project hourly rate persistence (no vs dependency).
"""

from __future__ import annotations

import json
import os
from typing import Dict

from vectortrack_config import load_paths_json, resolve_plugin_data_dir

try:
    from vectortrack_core.constants import DEFAULT_HOURLY_RATE as DEFAULT_RATE
    from vectortrack_core.paths.manifest import default_hourly_rate_from_paths
except ImportError:
    DEFAULT_RATE = 75.0

    def default_hourly_rate_from_paths(path):  # type: ignore[no-redef]
        return DEFAULT_RATE

RATES_FILENAME = "rates.json"


def get_rates_path(plugin_data_dir: str) -> str:
    os.makedirs(plugin_data_dir, exist_ok=True)
    return os.path.join(plugin_data_dir, RATES_FILENAME)


def load_rates(plugin_data_dir: str) -> Dict[str, float]:
    path = get_rates_path(plugin_data_dir)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return {str(k): float(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return {}


def save_rates(plugin_data_dir: str, rates: Dict[str, float]) -> None:
    path = get_rates_path(plugin_data_dir)
    os.makedirs(plugin_data_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(rates, handle, indent=2)


def _resolve_default_rate(vw_year: int) -> float:
    from pathlib import Path

    from vectortrack_config import paths_json_path

    paths_file = Path(paths_json_path(vw_year))
    if paths_file.is_file():
        try:
            return float(default_hourly_rate_from_paths(paths_file))
        except (TypeError, ValueError):
            pass
    payload = load_paths_json(vw_year)
    raw = payload.get("default_hourly_rate")
    try:
        if raw is not None:
            return float(raw)
    except (TypeError, ValueError):
        pass
    return DEFAULT_RATE


def get_rate(
    plugin_data_dir: str,
    project_name: str,
    vw_year: int | None = None,
    *,
    sync_folder: str | None = None,
    project_code: str | None = None,
) -> float:
    rates = load_rates(plugin_data_dir)
    if project_name in rates:
        return float(rates[project_name])
    if sync_folder and project_code:
        from vectortrack_config import hourly_rate_from_catalog

        catalog_rate = hourly_rate_from_catalog(sync_folder, project_code)
        if catalog_rate is not None:
            return catalog_rate
    if vw_year is not None:
        return _resolve_default_rate(vw_year)
    return DEFAULT_RATE


def set_rate(plugin_data_dir: str, project_name: str, rate: float) -> None:
    rates = load_rates(plugin_data_dir)
    rates[project_name] = float(rate)
    save_rates(plugin_data_dir, rates)


def plugin_data_dir_for_year(vw_year: int) -> str:
    return resolve_plugin_data_dir(vw_year)
