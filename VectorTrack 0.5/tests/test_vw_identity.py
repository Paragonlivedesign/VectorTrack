"""Tests for Vectorworks-derived machine identity."""

from __future__ import annotations

import json
from pathlib import Path

from vectortrack.services.vw_identity import (
    VWIdentity,
    clear_vw_identity_cache,
    hostname_hash_machine_id,
    is_legacy_hostname_machine_id,
    local_machine_id,
    resolve_sync_machine_id,
    resolve_sync_machine_label,
    resolve_vw_identity,
    vw_year_from_log_path,
)


def _write_identity_fixtures(root: Path, *, year: int = 2026) -> Path:
    data_dir = root / str(year)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "machine_uuid.txt").write_text(
        "08e696b5-f6a3-4f29-8dbf-da67024d0c2b\n",
        encoding="utf-8",
    )
    (data_dir / "US-G1MGJ7.ldf").write_text("license", encoding="utf-8")
    user_log = data_dir / "VW User Log.txt"
    lines = [
        {
            "ts": "06/24/2026 00:50:50 +0000",
            "sn": "EMXUSZ-XXXXXX-XXXXXX-G1MGJ7",
            "session": "019ef6312c82",
            "cat": "LDF",
            "message": "LicenseDescription::Open (result: 0, licenseID: US-G1MGJ7)",
        },
    ]
    user_log.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
    return data_dir


def test_vw_identity_from_fixtures(tmp_path, monkeypatch):
    data_dir = _write_identity_fixtures(tmp_path)
    monkeypatch.setattr(
        "vectortrack.services.vw_identity.vw_data_dir",
        lambda vw_year=None: data_dir if vw_year in (None, 2026) else tmp_path / str(vw_year),
    )
    clear_vw_identity_cache()

    identity = resolve_vw_identity(2026, refresh=True)
    assert identity.machine_uuid == "08e696b5-f6a3-4f29-8dbf-da67024d0c2b"
    assert identity.license_id == "US-G1MGJ7"
    assert identity.license_suffix == "G1MGJ7"
    assert identity.machine_id == "08e696b5-f6a3-4f29-8dbf-da67024d0c2b"
    assert identity.default_label.endswith("(G1MGJ7)")


def test_resolve_sync_machine_id_migrates_legacy_hash():
    legacy = hostname_hash_machine_id()
    assert is_legacy_hostname_machine_id(legacy) is True
    assert resolve_sync_machine_id(legacy) == local_machine_id()
    assert resolve_sync_machine_id("custom-machine") == "custom-machine"


def test_resolve_sync_machine_label_defaults_to_identity(tmp_path, monkeypatch):
    data_dir = _write_identity_fixtures(tmp_path)
    monkeypatch.setattr("vectortrack.services.vw_identity.vw_data_dir", lambda vw_year=None: data_dir)
    clear_vw_identity_cache()
    identity = resolve_vw_identity(2026, refresh=True)
    assert resolve_sync_machine_label("", 2026) == identity.default_label
    assert resolve_sync_machine_label("Office laptop", 2026) == "Office laptop"


def test_vw_year_from_log_path():
    assert vw_year_from_log_path(r"C:\Users\me\AppData\Roaming\Nemetschek\Vectorworks\2026\Vectorworks Log.txt") == 2026
    assert vw_year_from_log_path("/sync/machines/uuid/2025/Vectorworks Log.txt") == 2025


def test_identity_fallback_without_vectorworks_data(tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    monkeypatch.setattr("vectortrack.services.vw_identity.vw_data_dir", lambda vw_year=None: missing)
    clear_vw_identity_cache()
    identity = resolve_vw_identity(2026, refresh=True)
    assert identity.machine_uuid == ""
    assert identity.machine_id == hostname_hash_machine_id()
    assert isinstance(identity.default_label, str)
