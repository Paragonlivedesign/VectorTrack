"""Import/export service for .vtpack bundles."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ImportPreview:
    total_rows: int
    duplicate_rows: int
    importable_rows: int
    duplicate_keys: List[str]


class ImportExportService:
    """Export and import session data as .vtpack archives."""

    def export_vtpack(
        self,
        rows: Sequence[Dict[str, object]],
        output_path: str,
        metadata: Optional[Dict[str, object]] = None,
    ) -> str:
        payload = {
            "version": 1,
            "exported_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "rows": list(rows),
        }
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(payload, indent=2))
        return str(path)

    def read_vtpack(self, input_path: str) -> Dict[str, object]:
        with zipfile.ZipFile(input_path, "r") as archive:
            with archive.open("manifest.json", "r") as handle:
                return json.loads(handle.read().decode("utf-8"))

    def preview_import(
        self,
        input_path: str,
        existing_rows: Optional[Iterable[Dict[str, object]]] = None,
        key_fields: Sequence[str] = ("project_id", "file_path", "start_time"),
    ) -> ImportPreview:
        payload = self.read_vtpack(input_path)
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            rows = []

        existing_keys = {
            self._row_key(item, key_fields)
            for item in (existing_rows or [])
        }
        duplicate_keys: List[str] = []
        importable = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = self._row_key(row, key_fields)
            if key in existing_keys:
                duplicate_keys.append(key)
                continue
            importable += 1
        return ImportPreview(
            total_rows=len(rows),
            duplicate_rows=len(duplicate_keys),
            importable_rows=importable,
            duplicate_keys=duplicate_keys,
        )

    def import_rows(
        self,
        input_path: str,
        existing_rows: Optional[Iterable[Dict[str, object]]] = None,
        key_fields: Sequence[str] = ("project_id", "file_path", "start_time"),
    ) -> Tuple[List[Dict[str, object]], ImportPreview]:
        payload = self.read_vtpack(input_path)
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            rows = []

        existing_key_map = {
            self._row_key(item, key_fields)
            for item in (existing_rows or [])
        }
        importable_rows: List[Dict[str, object]] = []
        duplicate_keys: List[str] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = self._row_key(row, key_fields)
            if key in existing_key_map:
                duplicate_keys.append(key)
                continue
            importable_rows.append(row)
            existing_key_map.add(key)

        preview = ImportPreview(
            total_rows=len(rows),
            duplicate_rows=len(duplicate_keys),
            importable_rows=len(importable_rows),
            duplicate_keys=duplicate_keys,
        )
        return importable_rows, preview

    @staticmethod
    def _row_key(row: Dict[str, object], key_fields: Sequence[str]) -> str:
        return "|".join(str(row.get(field, "")) for field in key_fields)
