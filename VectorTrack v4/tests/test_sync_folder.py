"""Tests for VectorTrack v4 cross-machine sync helpers."""

from __future__ import annotations

from pathlib import Path

from vectortrack.log_parser import LOG_FILENAME
from vectortrack.sync_config import SyncConfig, sync_config_to_mapping
from vectortrack.sync_folder import gather_sync_log_paths, push_log_snapshot


def test_sync_config_mapping_roundtrip():
    config = SyncConfig(
        enabled=True,
        folder="G:/My Drive/VectorTrack/logs",
        machine_id="office-desktop",
        machine_label="Office Desktop",
    )
    restored = SyncConfig(**sync_config_to_mapping(config))
    assert restored.enabled is True
    assert restored.folder == config.folder
    assert restored.machine_id == config.machine_id


def test_gather_sync_log_paths_includes_remote(tmp_path):
    sync_folder = tmp_path / "cloud"
    local_log = tmp_path / "local" / LOG_FILENAME
    local_log.parent.mkdir(parents=True)
    local_log.write_text('Opened "Demo.vwx" at 6/1/2025 9:00:00 AM\n', encoding="utf-8")

    config_a = SyncConfig(enabled=True, folder=str(sync_folder), machine_id="machine-a")
    config_b = SyncConfig(enabled=True, folder=str(sync_folder), machine_id="machine-b")

    push_log_snapshot(str(local_log), config_a, 2026)

    other_log = tmp_path / "other" / LOG_FILENAME
    other_log.parent.mkdir(parents=True)
    other_log.write_text('Closed "Demo.vwx" at 6/1/2025 10:00:00 AM\n', encoding="utf-8")
    push_log_snapshot(str(other_log), config_b, 2026)

    paths, machine_count = gather_sync_log_paths([str(local_log)], config_a, 2026)
    assert machine_count == 2
    assert len(paths) == 2
