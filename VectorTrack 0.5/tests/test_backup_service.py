"""Tests for BackupService."""

from __future__ import annotations

import zipfile
from pathlib import Path

from vectortrack.services.backup_service import BackupService


def test_create_backup_and_restore(tmp_path: Path) -> None:
    source = tmp_path / "data"
    source.mkdir()
    db_file = source / "vectortrack.db"
    db_file.write_text("sqlite-data", encoding="utf-8")

    backup_dir = tmp_path / "backups"
    service = BackupService(backup_dir=str(backup_dir), retention_count=2)
    archive = service.create_backup([str(db_file)], label="test")

    assert Path(archive).is_file()
    with zipfile.ZipFile(archive, "r") as zf:
        assert "vectortrack.db" in zf.namelist()

    restore_dir = tmp_path / "restored"
    restored = service.restore_backup(archive, str(restore_dir), overwrite=True)
    assert restored
    assert (restore_dir / "vectortrack.db").read_text(encoding="utf-8") == "sqlite-data"


def test_backup_retention(tmp_path: Path) -> None:
    source = tmp_path / "file.txt"
    source.write_text("x", encoding="utf-8")
    service = BackupService(backup_dir=str(tmp_path / "backups"), retention_count=2)

    paths = [service.create_backup([str(source)], label=f"b{i}") for i in range(4)]
    listed = service.list_backups()
    assert len(listed) == 2
    assert paths[-1] in listed
    assert paths[0] not in listed
