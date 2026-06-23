"""
Per-project hourly rate persistence (no vs dependency).
"""

import json
import os
from typing import Dict, Optional

from vectortrack_config import resolve_plugin_data_dir

DEFAULT_RATE = 100.0
RATES_FILENAME = 'rates.json'


def get_rates_path(plugin_data_dir: str) -> str:
    os.makedirs(plugin_data_dir, exist_ok=True)
    return os.path.join(plugin_data_dir, RATES_FILENAME)


def load_rates(plugin_data_dir: str) -> Dict[str, float]:
    path = get_rates_path(plugin_data_dir)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return {str(k): float(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return {}


def save_rates(plugin_data_dir: str, rates: Dict[str, float]) -> None:
    path = get_rates_path(plugin_data_dir)
    os.makedirs(plugin_data_dir, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(rates, handle, indent=2)


def get_rate(plugin_data_dir: str, project_name: str) -> float:
    rates = load_rates(plugin_data_dir)
    return float(rates.get(project_name, DEFAULT_RATE))


def set_rate(plugin_data_dir: str, project_name: str, rate: float) -> None:
    rates = load_rates(plugin_data_dir)
    rates[project_name] = float(rate)
    save_rates(plugin_data_dir, rates)


def plugin_data_dir_for_year(vw_year: int) -> str:
    return resolve_plugin_data_dir(vw_year)
