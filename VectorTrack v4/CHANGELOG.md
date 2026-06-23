# Changelog

## [0.4.0-beta] — 2026-06

Beta release. Invited testers only; installer not code-signed.

Semver is **0.4.x** while in beta (not 4.0.0). Source folders: `VectorTrack v4/`, `VectorTrackScript v4/`.

### VectorTrack (desktop)

- Added Windows installer (`VectorTrack-0.4.0-Setup.exe`) via Inno Setup
- Added optional cross-machine log sync through a user-chosen cloud-synced folder
- Added `build.ps1` / `build_installer.ps1` packaging chain
- Added main-window smoke tests for CI
- PyInstaller build with app icon and explicit service/database hidden imports

### Shared / infrastructure

- Log snapshot format for multi-machine merge under `{sync_folder}/machines/{machine_id}/{year}/`
- Settings UI for sync folder, machine ID, and enable/disable

### Unchanged from 3.x

- Multi-file Vectorworks detection, idle monitoring, per-file rates
- SQLite session storage, PDF reports, light/dark themes

### Known limitations

- Time is not merged across revisions of the same project (save-as / duplicate filenames)
- No hosted sync service — folder sync is manual via cloud desktop clients
- Licensing enforcement disabled in beta builds (`ENFORCE_LICENSING = False`)
- Windows SmartScreen may block the unsigned installer on first run

---

## [3.0.0] — 2025

- Stabilized unit tests; GUI integration tests deferred
- Session DB persistence fixes
- File-specific settings dialog
- PyInstaller packaging; licensing simplified (no WMI dependency)

---

## Earlier versions

Pre-3.0 history (alpha through 1.x) is archived in `VectorTrack v0 PY/` and legacy folders in the development repository.
