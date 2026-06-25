"""Tests for VectorTrack 0.5 cross-machine sync helpers."""

from __future__ import annotations

from pathlib import Path

from vectortrack.log_parser import LOG_FILENAME
from vectortrack.sync_config import SyncConfig, sync_config_from_mapping, sync_config_to_mapping
from vectortrack.sync_folder import gather_sync_log_paths, push_log_snapshot


def test_sync_config_mapping_roundtrip():
    config = SyncConfig(
        enabled=True,
        folder="G:/My Drive/VectorTrack/logs",
        machine_id="office-desktop",
        machine_label="Office Desktop",
    )
    restored = sync_config_from_mapping(sync_config_to_mapping(config))
    assert restored.enabled is True
    assert Path(restored.folder) == Path(config.folder)
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


def test_gather_sync_log_paths_without_local_log(tmp_path):
    sync_folder = tmp_path / "cloud"
    remote_log = tmp_path / "other" / LOG_FILENAME
    remote_log.parent.mkdir(parents=True)
    remote_log.write_text('Closed "Demo.vwx" at 6/1/2025 10:00:00 AM\n', encoding="utf-8")

    config_remote = SyncConfig(enabled=True, folder=str(sync_folder), machine_id="remote-machine")
    push_log_snapshot(str(remote_log), config_remote, 2026)

    config_new = SyncConfig(enabled=True, folder=str(sync_folder), machine_id="new-machine")
    paths, machine_count = gather_sync_log_paths([], config_new, 2026)
    assert len(paths) == 1
    assert machine_count == 1
    assert any("remote-machine" in path for path in paths)


def test_gather_sync_log_paths_uses_own_snapshot_when_local_missing(tmp_path):
    sync_folder = tmp_path / "cloud"
    prior_log = tmp_path / "prior" / LOG_FILENAME
    prior_log.parent.mkdir(parents=True)
    prior_log.write_text('Opened "Demo.vwx" at 6/1/2025 9:00:00 AM\n', encoding="utf-8")

    machine_id = "same-machine"
    config = SyncConfig(enabled=True, folder=str(sync_folder), machine_id=machine_id)
    push_log_snapshot(str(prior_log), config, 2026)

    paths, machine_count = gather_sync_log_paths([], config, 2026)
    assert len(paths) == 1
    assert machine_count == 1
    assert machine_id in paths[0]
