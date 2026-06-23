# VectorTrack

Time tracking built around Vectorworks workflow — a Windows desktop app and an in-app menu command that read the same activity logs.

| | |
|---|---|
| **Release** | 0.4.0 beta |
| **Updated** | June 2026 |
| **Publisher** | [Paragon Live Design](https://paragonlivedesign.com) |
| **Support** | Cody@Paragonlivedesign.com |

> **Beta.** Builds are for internal and invited testers. Windows may show a SmartScreen warning because the installer is not code-signed yet. Expect rough edges; report issues to support.

---

## Versioning

Pre-1.0 beta releases use **`0.4.x`** semver (e.g. `0.4.0`, `0.4.1`). Source lives in **`VectorTrack v4/`** and **`VectorTrackScript v4/`** — the `v4` folder name is the product generation; the semver is the release number.

---

## Products

Two installs, same problem domain. Use either one or both.

| Product | Install target | Docs |
|---------|----------------|------|
| **VectorTrack** | Windows 10+ desktop | [`VectorTrack v4/README.md`](VectorTrack%20v4/README.md) |
| **VectorTrackScript** | Vectorworks plug-in (2025 / 2026 tested) | [`VectorTrackScript v4/README.md`](VectorTrackScript%20v4/README.md) |

**VectorTrack** watches open Vectorworks documents, tracks active vs idle time, stores sessions locally, and exports PDF reports.

**VectorTrackScript** opens a summary dialog inside Vectorworks for the file you have open — sessions, rates, budget, and copy-to-clipboard for billing.

Neither product requires the other.

---

## 0.4.0 beta — changes

### VectorTrack (desktop)

- Windows installer (`VectorTrack-0.4.0-Setup.exe`) and portable build
- Optional cross-machine log sync through a cloud-synced folder (Drive / Dropbox / OneDrive)
- PyInstaller packaging with explicit imports for services and SQLite
- Main-window smoke tests in CI

Carried over from 3.x: multi-file detection, idle timeout, per-file rates, SQLite storage, PDF reports, light/dark themes.

### VectorTrackScript (plug-in)

- Client, budget, and trust-note fields in the summary dialog
- Alias-aware parsing when project files are renamed or saved-as
- Copy-to-clipboard for invoice and email workflows
- Cross-machine log sync with in-app **Sync...** settings
- Project metadata and aliases via `paths.json`

Carried over from 3.x: menu-command `.vsm` install, automatic log path detection by Vectorworks year, per-project rates in `rates.json`.

### Not in 0.4

- Merging time across revisions of the same project file
- Hosted sync or payment/licensing infrastructure

Full history: [`VectorTrack v4/CHANGELOG.md`](VectorTrack%20v4/CHANGELOG.md)

---

## Quick start

**Desktop app** — build from [`VectorTrack v4/`](VectorTrack%20v4/) or run the packaged beta build if your tester package includes `VectorTrack-0.4.0-Setup.exe`.

**Vectorworks plug-in** — follow [`VectorTrackScript v4/README.md`](VectorTrackScript%20v4/README.md). Register the `.vsm` wrapper once in Plug-in Manager; Python sources ship in-repo.

---

## Repository layout

| Path | Contents |
|------|----------|
| `VectorTrack v4/` | PyQt6 desktop app source (current beta) |
| `VectorTrackScript v4/` | In-Vectorworks Python plug-in source (current beta) |
| `VectorTrack v0 PY/` | Original alpha — reference only |
| `V.0/`, `v1.0/`, `TimeTracker*.py` | Earlier prototypes |

---

## Requirements

| Component | Requirement |
|-----------|-------------|
| VectorTrack | Windows 10 or later |
| VectorTrack (dev) | Python 3.10+, dependencies in `VectorTrack v4/requirements.txt` |
| VectorTrackScript | Vectorworks with Python scripting (2025 / 2026 verified) |

---

## Build (developers)

```powershell
# Desktop app
cd "VectorTrack v4"
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m vectortrack

# Package desktop app + installer
.\build.ps1 -WithInstaller

# Vectorworks plug-in zip
cd "..\VectorTrackScript v4"
.\package_plugin.ps1
```

---

## License

See [`VectorTrack v4/EULA.md`](VectorTrack%20v4/EULA.md). Beta builds may include licensing hooks that are disabled in current test builds.
