"""Tests for cross-machine log sync (no Vectorworks required)."""

import json
import os
import sys
from datetime import datetime

import pytest

SCRIPT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_ROOT not in sys.path:
    sys.path.insert(0, SCRIPT_ROOT)

from vectortrack_config import SyncConfig, load_sync_config, save_sync_config
from vectortrack_log import LOG_FILENAME, merge_log_contents, parse_sessions_from_sources
from vectortrack_sync import (
    discover_remote_log_paths,
    gather_log_sources_for_sync,
    push_log_snapshot,
    snapshot_path,
)


def test_load_sync_config_defaults(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    paths_file = plugin_dir / "paths.json"
    paths_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "vectortrack_config.plugin_data_dir_for_year",
        lambda _year, _folder=None: str(plugin_dir),
    )
    config = load_sync_config(2026)
    assert config.enabled is False
    assert config.folder == ""
    assert config.sync_on_refresh is True
    assert config.machine_id == ""


def test_load_sync_config_from_paths_json(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    payload = {
        "sync": {
            "enabled": True,
            "folder": str(tmp_path / "cloud"),
            "machine_id": "office-desktop",
            "machine_label": "Office Desktop",
            "sync_on_refresh": False,
        }
    }
    (plugin_dir / "paths.json").write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(
        "vectortrack_config.plugin_data_dir_for_year",
        lambda _year, _folder=None: str(plugin_dir),
    )
    config = load_sync_config(2026)
    assert config.enabled is True
    assert config.folder == str(tmp_path / "cloud")
    assert config.machine_id == "office-desktop"
    assert config.machine_label == "Office Desktop"
    assert config.sync_on_refresh is False


def test_save_sync_config_writes_paths_json(tmp_path, monkeypatch):
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    monkeypatch.setattr(
        "vectortrack_config.plugin_data_dir_for_year",
        lambda _year, _folder=None: str(plugin_dir),
    )
    config = SyncConfig(
        enabled=True,
        folder=str(tmp_path / "cloud"),
        machine_id="office-desktop",
        machine_label="Office Desktop",
    )
    written = save_sync_config(2026, config)
    assert os.path.isfile(written)
    reloaded = load_sync_config(2026)
    assert reloaded.enabled is True
    assert reloaded.folder == str(tmp_path / "cloud")
    assert reloaded.machine_id == "office-desktop"


def test_merge_log_contents_deduplicates_duplicate_snapshots():
    log_a = '\n'.join(
        [
            'Opened "TestProject.vwx" at 6/1/2025 9:00:00 AM',
            'Closed "TestProject.vwx" at 6/1/2025 10:00:00 AM',
        ]
    )
    merged = merge_log_contents([log_a, log_a])
    now = datetime(2025, 6, 2, 12, 0, 0)
    sessions, total = parse_sessions_from_sources([merged], "TestProject.vwx", now=now)
    assert len(sessions) == 1
    assert total == pytest.approx(1.0, abs=0.01)


def test_merge_log_contents_combines_two_machines():
    machine_a = '\n'.join(
        [
            'Opened "TestProject.vwx" at 6/1/2025 9:00:00 AM',
            'Closed "TestProject.vwx" at 6/1/2025 10:00:00 AM',
        ]
    )
    machine_b = '\n'.join(
        [
            'Opened "TestProject.vwx" at 6/2/2025 1:00:00 PM',
            'Closed "TestProject.vwx" at 6/2/2025 3:00:00 PM',
        ]
    )
    sessions, total = parse_sessions_from_sources(
        [machine_a, machine_b],
        "TestProject.vwx",
    )
    assert len(sessions) == 2
    assert total == pytest.approx(3.0, abs=0.01)


def test_merge_log_contents_open_on_one_machine_close_on_other():
    machine_a = 'Opened "TestProject.vwx" at 6/1/2025 9:00:00 AM'
    machine_b = 'Closed "TestProject.vwx" at 6/1/2025 11:00:00 AM'
    sessions, total = parse_sessions_from_sources(
        [machine_a, machine_b],
        "TestProject.vwx",
    )
    assert len(sessions) == 1
    assert total == pytest.approx(2.0, abs=0.01)


def test_push_and_discover_remote_snapshots(tmp_path):
    sync_folder = tmp_path / "cloud"
    local_log = tmp_path / "local" / LOG_FILENAME
    local_log.parent.mkdir(parents=True)
    local_log.write_text("Opened \"Demo.vwx\" at 6/1/2025 9:00:00 AM\n", encoding="utf-8")

    config_a = SyncConfig(
        enabled=True,
        folder=str(sync_folder),
        machine_id="machine-a",
        machine_label="Machine A",
    )
    config_b = SyncConfig(
        enabled=True,
        folder=str(sync_folder),
        machine_id="machine-b",
        machine_label="Machine B",
    )

    ok, message = push_log_snapshot(str(local_log), config_a, 2026)
    assert ok is True
    assert message == ""

    snapshot = snapshot_path(str(sync_folder), "machine-a", 2026)
    assert os.path.isfile(snapshot)
    meta_path = os.path.join(os.path.dirname(snapshot), "sync_meta.json")
    assert os.path.isfile(meta_path)
    with open(meta_path, encoding="utf-8") as handle:
        meta = json.load(handle)
    assert meta["machine_id"] == "machine-a"
    assert meta["byte_size"] > 0

    remote = discover_remote_log_paths(str(sync_folder), "machine-b", 2026)
    assert remote == [snapshot]

    other_log = tmp_path / "other" / LOG_FILENAME
    other_log.parent.mkdir(parents=True)
    other_log.write_text("Closed \"Demo.vwx\" at 6/1/2025 10:00:00 AM\n", encoding="utf-8")
    push_log_snapshot(str(other_log), config_b, 2026)

    sources, machine_count, note = gather_log_sources_for_sync(
        str(local_log),
        config_a,
        2026,
    )
    assert note is None
    assert machine_count == 2
    assert len(sources) == 2

    sessions, total = parse_sessions_from_sources(sources, "Demo.vwx")
    assert len(sessions) == 1
    assert total == pytest.approx(1.0, abs=0.01)


def test_gather_log_sources_missing_sync_folder(tmp_path):
    local_log = tmp_path / LOG_FILENAME
    local_log.write_text("Opened \"Demo.vwx\" at 6/1/2025 9:00:00 AM\n", encoding="utf-8")

    config = SyncConfig(
        enabled=True,
        folder=str(tmp_path / "missing-folder"),
        machine_id="machine-a",
        sync_on_refresh=False,
    )
    sources, machine_count, note = gather_log_sources_for_sync(str(local_log), config, 2026)
    assert len(sources) == 1
    assert machine_count == 1
    assert note == "Sync folder unavailable — local log only"


def test_gather_log_sources_sync_disabled(tmp_path):
    local_log = tmp_path / LOG_FILENAME
    local_log.write_text("Opened \"Demo.vwx\" at 6/1/2025 9:00:00 AM\n", encoding="utf-8")

    config = SyncConfig(enabled=False)
    sources, machine_count, note = gather_log_sources_for_sync(str(local_log), config, 2026)
    assert len(sources) == 1
    assert machine_count == 1
    assert note is None
