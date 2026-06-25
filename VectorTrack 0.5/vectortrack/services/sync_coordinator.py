"""Coordinates cross-machine sync operations for the desktop app."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Callable, Optional

from vectortrack.services.catalog_sync import (
    CatalogApplySummary,
    build_catalog_view,
    filter_orphan_project_codes,
    push_catalog,
    read_catalog,
    sync_catalog,
)
from vectortrack.services.project_sync import sync_orphan_project_codes
from vectortrack.services.vw_identity import resolve_sync_machine_id, resolve_sync_machine_label
from vectortrack.sync_config import SyncConfig, load_sync_config_from_paths_json
from vectortrack.sync_folder import (
    catalog_path,
    load_sync_machine_labels,
    merge_remote_assignments,
    migrate_legacy_hostname_snapshot,
    push_assignments_snapshot,
    push_log_snapshot,
    resolve_machine_display,
    resolve_sync_folder,
    snapshot_dir,
)
from vectortrack import config


StatusCallback = Callable[[str, int], None]


class SyncCoordinator:
    def __init__(
        self,
        *,
        repository: object,
        settings_store: object,
        log_paths_provider: Callable[[], list[str]],
        vw_year_provider: Callable[[], int],
        status_callback: Optional[StatusCallback] = None,
    ) -> None:
        self.repository = repository
        self.settings_store = settings_store
        self.log_paths_provider = log_paths_provider
        self.vw_year_provider = vw_year_provider
        self.status_callback = status_callback or (lambda _msg, _ms: None)

        self.sync_config = SyncConfig()
        self.file_project_overrides: dict[str, str] = {}
        self.merged_assignments: dict[str, str] = {}
        self._machine_label_cache: dict[str, str] = {}
        self._catalog_dirty = False
        self._assignments_dirty = False
        self._cached_catalog: dict | None = None
        self._cached_catalog_folder = ""
        self._cached_catalog_mtime = 0.0
        self._cached_catalog_diff = None
        self._cached_catalog_diff_at = datetime.min
        self._last_catalog_maintenance_at = datetime.min
        self._last_sync_push = datetime.min
        self._last_sync_push_error = ""

    def load_config(self) -> SyncConfig:
        settings = self.settings_store.qsettings
        vw_year = self.vw_year_provider()
        if settings.contains("sync_enabled"):
            stored_id = str(settings.value("sync_machine_id", "", type=str))
            stored_label = str(settings.value("sync_machine_label", "", type=str))
            from vectortrack.sync_config import default_machine_id

            self.sync_config = SyncConfig(
                enabled=settings.value("sync_enabled", False, type=bool),
                folder=settings.value("sync_folder", "", type=str),
                machine_id=resolve_sync_machine_id(stored_id or default_machine_id(), vw_year),
                machine_label=resolve_sync_machine_label(stored_label, vw_year),
                sync_on_refresh=settings.value("sync_on_refresh", True, type=bool),
            )
        else:
            loaded = load_sync_config_from_paths_json(config.paths_json_path())
            self.sync_config = SyncConfig(
                enabled=loaded.enabled,
                folder=loaded.folder,
                machine_id=resolve_sync_machine_id(loaded.machine_id, vw_year),
                machine_label=resolve_sync_machine_label(loaded.machine_label, vw_year),
                sync_on_refresh=loaded.sync_on_refresh,
            )
        sync_folder = resolve_sync_folder(self.sync_config)
        if sync_folder:
            migrate_legacy_hostname_snapshot(sync_folder, self.sync_config.machine_id, vw_year)
        return self.sync_config

    def mark_catalog_dirty(self) -> None:
        self._catalog_dirty = True
        self._cached_catalog_diff = None

    def invalidate_catalog_cache(self) -> None:
        self._cached_catalog = None
        self._cached_catalog_diff = None

    def mark_assignments_dirty(self) -> None:
        self._assignments_dirty = True

    def _read_cached_catalog(self, sync_folder: str) -> dict:
        path = catalog_path(sync_folder)
        try:
            mtime = os.path.getmtime(path) if os.path.isfile(path) else 0.0
        except OSError:
            mtime = 0.0
        if (
            self._cached_catalog is not None
            and self._cached_catalog_folder == sync_folder
            and self._cached_catalog_mtime == mtime
        ):
            return self._cached_catalog
        catalog = read_catalog(sync_folder)
        self._cached_catalog = catalog
        self._cached_catalog_folder = sync_folder
        self._cached_catalog_mtime = mtime
        self._cached_catalog_diff = None
        return catalog

    def catalog_diff(self, *, force: bool = False):
        sync_folder = resolve_sync_folder(self.sync_config)
        if not sync_folder or not self.sync_config.enabled or not os.path.isdir(sync_folder):
            return None
        if (
            not force
            and not self._catalog_dirty
            and self._cached_catalog_diff is not None
            and (datetime.now() - self._cached_catalog_diff_at).total_seconds() < 60
        ):
            return self._cached_catalog_diff
        catalog = self._read_cached_catalog(sync_folder)
        self._cached_catalog_diff = build_catalog_view(self.repository, catalog)
        self._cached_catalog_diff_at = datetime.now()
        return self._cached_catalog_diff

    def maybe_push_catalog(self, *, force: bool = False) -> None:
        if not self.sync_config.enabled or not self.sync_config.folder.strip():
            return
        if not force and not self._catalog_dirty:
            return
        sync_folder = resolve_sync_folder(self.sync_config)
        if not sync_folder:
            return
        ok, _err = push_catalog(sync_folder, self.repository)
        if ok:
            self._catalog_dirty = False
            self.invalidate_catalog_cache()

    def sync_catalog_roundtrip(self) -> None:
        sync_folder = resolve_sync_folder(self.sync_config)
        if not sync_folder or not self.sync_config.enabled or not os.path.isdir(sync_folder):
            return
        _summary, ok, err = sync_catalog(sync_folder, self.repository)
        if ok:
            self._catalog_dirty = False
            self.invalidate_catalog_cache()
        elif err:
            self.status_callback(f"Catalog sync failed: {err}", 8000)

    def refresh_merged_assignments(self, *, force_catalog_maintenance: bool = False) -> None:
        sync_folder = resolve_sync_folder(self.sync_config)
        vw_year = self.vw_year_provider()
        if sync_folder and self.sync_config.enabled:
            self.merged_assignments = merge_remote_assignments(
                sync_folder,
                vw_year,
                self.file_project_overrides,
                local_machine_id=self.sync_config.machine_id,
            )
            self._machine_label_cache = load_sync_machine_labels(sync_folder, vw_year)
        else:
            self.merged_assignments = {
                os.path.basename(str(path).replace("\\", "/")): str(code).strip()
                for path, code in self.file_project_overrides.items()
                if path and code
            }
            self._machine_label_cache = {}
        now = datetime.now()
        if force_catalog_maintenance or (
            now - self._last_catalog_maintenance_at
        ).total_seconds() >= 120:
            self._last_catalog_maintenance_at = now

    def maybe_push_assignments(self, *, force: bool = False) -> None:
        if not self.sync_config.enabled or not self.sync_config.folder.strip():
            return
        if not force and not self._assignments_dirty:
            return
        ok, _err = push_assignments_snapshot(
            self.file_project_overrides,
            self.sync_config,
            self.vw_year_provider(),
        )
        if ok:
            self._assignments_dirty = False

    def maybe_push_log_sync(self, *, force: bool = False) -> bool:
        if not self.sync_config.enabled or not self.sync_config.sync_on_refresh:
            return False
        if not self.sync_config.folder.strip():
            self._last_sync_push_error = "Sync folder is not set"
            return False
        if not force and (datetime.now() - self._last_sync_push).total_seconds() < 60:
            return False

        paths = self.log_paths_provider()
        if not paths:
            self._last_sync_push_error = "Vectorworks Log.txt not found on this machine"
            return False

        ok, err = push_log_snapshot(paths[0], self.sync_config, self.vw_year_provider())
        if ok:
            self._last_sync_push = datetime.now()
            self._last_sync_push_error = ""
            dest = snapshot_dir(
                self.sync_config.folder.strip(),
                self.sync_config.machine_id,
                self.vw_year_provider(),
            )
            self.status_callback(f"Log sync updated: {dest}", 4000)
            return True

        self._last_sync_push_error = err or "Unknown sync error"
        self.status_callback(f"Log sync failed: {self._last_sync_push_error}", 8000)
        return False

    def machine_display(self, machine_id: str) -> str:
        sync_folder = resolve_sync_folder(self.sync_config)
        return resolve_machine_display(
            machine_id,
            sync_folder=sync_folder,
            vw_year=self.vw_year_provider(),
            local_config=self.sync_config,
            label_cache=self._machine_label_cache,
        )

    def show_catalog_sync_summary(self, summary: CatalogApplySummary) -> None:
        if not summary.has_changes:
            return
        parts: list[str] = []
        if summary.clients_added:
            parts.append(f"{summary.clients_added} client(s) added")
        if summary.clients_updated:
            parts.append(f"{summary.clients_updated} client(s) updated")
        if summary.projects_added:
            parts.append(f"{summary.projects_added} project(s) added")
        if summary.projects_updated:
            parts.append(f"{summary.projects_updated} project(s) updated")
        if summary.fuzzy_merged:
            pair = summary.fuzzy_merged[0]
            parts.append(f"merged similar client '{pair[0]}' → '{pair[1]}'")
            if len(summary.fuzzy_merged) > 1:
                parts.append(f"(+{len(summary.fuzzy_merged) - 1} more)")
        self.status_callback(f"Catalog sync: {', '.join(parts)}", 6000)

    def sync_orphan_projects(self, *, default_rate: float) -> tuple[list[str], list[str]]:
        codes: set[str] = set()
        for code in self.file_project_overrides.values():
            if code:
                codes.add(str(code).strip())
        for code in self.merged_assignments.values():
            if code:
                codes.add(str(code).strip())
        for session in self.repository.list_sessions(include_open=True, limit=15000):
            if session.project_id:
                codes.add(str(session.project_id).strip())

        missing_codes = [
            code
            for code in sorted(codes)
            if code and self.repository.get_project_by_code(code) is None
        ]
        catalog = {}
        sync_folder = resolve_sync_folder(self.sync_config)
        if sync_folder and self.sync_config.enabled and os.path.isdir(sync_folder):
            catalog = self._read_cached_catalog(sync_folder)

        stub_codes, catalog_only = filter_orphan_project_codes(missing_codes, catalog)
        created = sync_orphan_project_codes(self.repository, stub_codes, default_rate=default_rate)
        return created, catalog_only

    def tick(self, *, force_log_sync: bool = False) -> None:
        self.maybe_push_log_sync(force=force_log_sync)
        self.maybe_push_assignments()
        self.maybe_push_catalog()
