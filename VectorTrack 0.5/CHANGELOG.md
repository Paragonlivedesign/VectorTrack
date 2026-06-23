# Changelog

## [0.5.3-beta] — 2026-06

### VectorTrack (desktop)

- **Fix crash with Vectorworks open** — removed deep child-window walk (VW 2026 has hundreds of HWNDs); parse file name from main window title only
- **Performance** — one window scan per tick instead of two or three
- Safer Win32 calls with invalid-handle checks and refresh error recovery
- Installer artifact: `VectorTrack-0.5.3-Setup.exe`

### VectorTrackScript (plug-in)

- Version aligned to **0.5.3 beta**

---

## [0.5.2-beta] — 2026-06

### VectorTrack (desktop)

- **Stability** — hotkey handlers run on the main UI thread; single keyboard listener when hotkeys are enabled (fixes intermittent crashes)
- **Status bar** — version shown bottom-left instead of licensing debug text
- Uncaught Python exceptions logged to `vectortrack.log`
- Installer artifact: `VectorTrack-0.5.2-Setup.exe`

### VectorTrackScript (plug-in)

- Version aligned to **0.5.2 beta**

---

## [0.5.1-beta] — 2026-06

### VectorTrack (desktop)

- **Single-instance guard** — launching again raises the existing window instead of opening a second copy
- Updated application icons (tray, About dialog, window)
- **Logs and reports stored in AppData** — fixes startup and export failures when installed under Program Files
- **Vectorworks setup prompts** — link dialog when auto-detect fails; toast when it succeeds
- **Log Library** — shows auto-linked Vectorworks Log.txt paths with open file/folder actions
- **Idle detection settings** — optional pause when idle, configurable bypass when Vectorworks is foreground, a file is open, or the log shows open
- **Reports** — Master Summary, Project Detail, and Client Statement types; improved filtering and export
- **`dev.ps1`** — run from source during development without reinstalling
- Installer artifact: `VectorTrack-0.5.1-Setup.exe`

### VectorTrackScript (plug-in)

- Version aligned to **0.5.1 beta**

### Repository

- Added [`docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md) — versioning, branches, and release checklist

---

## [0.5.0-beta] — 2026-06

### Repository

- Legacy prototypes and alpha code moved to the `archive` branch; `main` is active 0.5 source only
- Renamed folders to `VectorTrack 0.5/` and `VectorTrackScript 0.5/`
- Beta builds distributed via GitHub Releases (installer + plug-in zip); `release/` is local build output only
- Removed local build scratch dirs from version control

### VectorTrack (desktop)

- Open Files and project summaries show **project names** instead of project numbers
- **Project numbers are optional** when creating projects (name is required)
- Installer artifact: `VectorTrack-0.5.0-Setup.exe`

### VectorTrackScript (plug-in)

- Version aligned to **0.5.0 beta**

---

## [0.4.0-beta] — 2026-06

Beta release. Invited testers only; installer not code-signed.

Semver is **0.4.x** while in beta (not 4.0.0). Source folders were `VectorTrack v4/`, `VectorTrackScript v4/`.

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

Pre-3.0 history (alpha through 1.x) is on the [`archive`](https://github.com/Paragonlivedesign/VectorTrack/tree/archive) branch.
