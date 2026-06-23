from __future__ import annotations

from vectortrack.services.import_export import ImportExportService


def test_export_and_read_vtpack(tmp_path):
    service = ImportExportService()
    rows = [
        {"project_id": "A1", "file_path": "x.vwx", "start_time": "2026-06-01T08:00:00"},
        {"project_id": "A2", "file_path": "y.vwx", "start_time": "2026-06-01T09:00:00"},
    ]

    output = tmp_path / "sample.vtpack"
    written = service.export_vtpack(rows, str(output), metadata={"source": "test"})
    payload = service.read_vtpack(written)

    assert payload["version"] == 1
    assert payload["metadata"]["source"] == "test"
    assert len(payload["rows"]) == 2


def test_preview_and_import_filter_duplicates(tmp_path):
    service = ImportExportService()
    rows = [
        {"project_id": "A1", "file_path": "x.vwx", "start_time": "2026-06-01T08:00:00"},
        {"project_id": "A1", "file_path": "x.vwx", "start_time": "2026-06-01T08:00:00"},
        {"project_id": "A1", "file_path": "z.vwx", "start_time": "2026-06-01T10:00:00"},
    ]
    output = tmp_path / "dupes.vtpack"
    service.export_vtpack(rows, str(output))
    existing = [{"project_id": "A1", "file_path": "x.vwx", "start_time": "2026-06-01T08:00:00"}]

    preview = service.preview_import(str(output), existing_rows=existing)
    imported_rows, summary = service.import_rows(str(output), existing_rows=existing)

    assert preview.total_rows == 3
    assert preview.duplicate_rows == 2
    assert preview.importable_rows == 1
    assert len(imported_rows) == 1
    assert imported_rows[0]["file_path"] == "z.vwx"
    assert summary.duplicate_rows == 2
