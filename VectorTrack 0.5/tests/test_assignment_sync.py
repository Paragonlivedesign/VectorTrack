"""Tests for cross-machine assignment sync and machine label resolution."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from vectortrack.sync_config import SyncConfig
from vectortrack.sync_folder import (
    ASSIGNMENTS_FILENAME,
    SYNC_META_FILENAME,
    merge_remote_assignments,
    push_assignments_snapshot,
    resolve_machine_display,
    snapshot_dir,
)


def _write_assignments(path: Path, assignments: dict[str, str], updated_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "updated_at": updated_at,
                "license_id": "US-TEST",
                "assignments": assignments,
            }
        ),
        encoding="utf-8",
    )


def test_merge_remote_assignments_last_write_wins(tmp_path):
    sync_folder = tmp_path / "sync"
    machine_a = "machine-a"
    machine_b = "machine-b"
    vw_year = 2026

    older = (datetime.now() - timedelta(hours=2)).isoformat(timespec="seconds")
    newer = datetime.now().isoformat(timespec="seconds")

    _write_assignments(
        Path(snapshot_dir(str(sync_folder), machine_a, vw_year)) / ASSIGNMENTS_FILENAME,
        {"Shared.vwx": "OLD"},
        older,
    )
    _write_assignments(
        Path(snapshot_dir(str(sync_folder), machine_b, vw_year)) / ASSIGNMENTS_FILENAME,
        {"Shared.vwx": "NEW"},
        newer,
    )

    merged = merge_remote_assignments(
        str(sync_folder),
        vw_year,
        {},
    )
    assert merged["Shared.vwx"] == "NEW"


def test_merge_remote_assignments_local_overrides_remote(tmp_path):
    sync_folder = tmp_path / "sync"
    vw_year = 2026
    newer = datetime.now().isoformat(timespec="seconds")
    _write_assignments(
        Path(snapshot_dir(str(sync_folder), "remote", vw_year)) / ASSIGNMENTS_FILENAME,
        {"Shared.vwx": "REMOTE"},
        newer,
    )

    merged = merge_remote_assignments(
        str(sync_folder),
        vw_year,
        {r"C:\Projects\Shared.vwx": "LOCAL"},
        local_machine_id="local-id",
    )
    assert merged["Shared.vwx"] == "LOCAL"


def test_push_assignments_snapshot_writes_basename_keys(tmp_path):
    sync_folder = tmp_path / "sync"
    config = SyncConfig(
        enabled=True,
        folder=str(sync_folder),
        machine_id="uuid-1234",
        machine_label="Office (TEST)",
    )
    ok, err = push_assignments_snapshot(
        {
            r"D:\Work\62026 Main.vwx": "62026",
            r"E:\Meeting Notes.vwx": "Meeting",
        },
        config,
        2026,
    )
    assert ok, err
    dest = Path(snapshot_dir(str(sync_folder), "uuid-1234", 2026)) / ASSIGNMENTS_FILENAME
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["assignments"]["62026 Main.vwx"] == "62026"
    assert payload["assignments"]["Meeting Notes.vwx"] == "Meeting"


def test_resolve_machine_display_uses_sync_meta(tmp_path):
    sync_folder = tmp_path / "sync"
    vw_year = 2026
    machine_id = "08e696b5-f6a3-4f29-8dbf-da67024d0c2b"
    meta_dir = Path(snapshot_dir(str(sync_folder), machine_id, vw_year))
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / SYNC_META_FILENAME).write_text(
        json.dumps(
            {
                "machine_label": "BlackTower (G1MGJ7)",
                "license_id": "US-G1MGJ7",
            }
        ),
        encoding="utf-8",
    )
    local = SyncConfig(enabled=True, folder=str(sync_folder), machine_id="local-id", machine_label="Local")
    label = resolve_machine_display(
        machine_id,
        sync_folder=str(sync_folder),
        vw_year=vw_year,
        local_config=local,
    )
    assert label == "BlackTower (G1MGJ7)"


def test_resolve_machine_display_local_machine_uses_config_label(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "vectortrack.sync_folder.resolve_sync_machine_label",
        lambda stored, vw_year=None: stored or "Default Host (ABCD)",
    )
    local = SyncConfig(
        enabled=True,
        folder=str(tmp_path),
        machine_id="local-id",
        machine_label="Office Laptop",
    )
    label = resolve_machine_display(
        "local-id",
        sync_folder=str(tmp_path),
        vw_year=2026,
        local_config=local,
    )
    assert label == "Office Laptop"
