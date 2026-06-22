"""Backup and restore service for VectorTrack data."""

from __future__ import annotations

import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable, List


class BackupService:
    """Create and restore zip backups with retention."""

    def __init__(self, backup_dir: str = "backups", retention_count: int = 10):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.retention_count = retention_count

    def create_backup(self, paths: Iterable[str], label: str = "vectortrack") -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{label}_{timestamp}.zip"
        with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for raw_path in paths:
                path = Path(raw_path)
                if not path.exists():
                    continue
                if path.is_dir():
                    for file_path in path.rglob("*"):
                        if file_path.is_file():
                            relative = file_path.relative_to(path)
                            arcname = os.path.join(path.name, str(relative)).replace("\\", "/")
                            archive.write(file_path, arcname=arcname)
                else:
                    archive.write(path, arcname=path.name)
        self._enforce_retention()
        return str(backup_path)

    def list_backups(self) -> List[str]:
        backups = sorted(self.backup_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [str(path) for path in backups]

    def restore_backup(self, backup_path: str, target_dir: str, overwrite: bool = False) -> List[str]:
        restored: List[str] = []
        destination = Path(target_dir)
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(backup_path, "r") as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                out_path = destination / member.filename
                out_path.parent.mkdir(parents=True, exist_ok=True)
                if out_path.exists() and not overwrite:
                    continue
                with archive.open(member, "r") as src, open(out_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                restored.append(str(out_path))
        return restored

    def _enforce_retention(self) -> None:
        if self.retention_count <= 0:
            return
        backups = sorted(self.backup_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        for stale in backups[self.retention_count :]:
            stale.unlink(missing_ok=True)
