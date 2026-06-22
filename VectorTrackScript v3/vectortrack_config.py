"""
VectorTrackScript v4 configuration helpers (paths.json + project metadata).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, Optional

PLUGIN_FOLDER = "VectorTrackScript v4"
PATHS_FILENAME = "paths.json"


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

