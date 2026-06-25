"""Tests for VectorTrackScript configuration helpers."""

from __future__ import annotations

import json
from pathlib import Path

from vectortrack_config import (
    SyncConfig,
    default_machine_id,
    hourly_rate_from_catalog,
    save_sync_config,
)


def test_default_machine_id_is_non_empty() -> None:
    assert default_machine_id()


def test_hourly_rate_from_catalog(tmp_path: Path) -> None:
    catalog = {
        "projects": [
            {"project_code": "PRJ-1", "hourly_rate": 125.0},
        ]
    }
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    rate = hourly_rate_from_catalog(str(tmp_path), "PRJ-1")
    assert rate == 125.0


def test_save_sync_config_writes_paths_json(tmp_path: Path, monkeypatch) -> None:
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    paths_file = plugin_dir / "paths.json"

    def fake_paths_json_path(vw_year, plugin_folder="VectorTrackScript 0.5"):
        return str(paths_file)

    monkeypatch.setattr("vectortrack_config.paths_json_path", fake_paths_json_path)
    monkeypatch.setattr("vectortrack_config.plugin_data_dir_for_year", lambda *_a, **_k: str(plugin_dir))

    config = SyncConfig(enabled=True, folder=str(tmp_path / "sync"), machine_id="abc", machine_label="Test")
    save_sync_config(2026, config)
    payload = json.loads(paths_file.read_text(encoding="utf-8"))
    assert payload["sync"]["enabled"] is True
    assert payload["sync"]["machine_id"] == "abc"
