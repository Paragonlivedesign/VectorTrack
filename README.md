# VectorTrack

Time tracking built around Vectorworks workflow — a Windows desktop app and an in-app menu command that read the same activity logs.

| | |
|---|---|
| **Release** | 0.5.0 beta |
| **Updated** | June 2026 |
| **Publisher** | [Paragon Live Design](https://paragonlivedesign.com) |
| **Support** | Cody@Paragonlivedesign.com |

> **Beta.** Builds are for internal and invited testers. Windows may show a SmartScreen warning because the installer is not code-signed yet. Expect rough edges; report issues to support.

---

## Versioning

Pre-1.0 beta releases use **`0.5.x`** semver (e.g. `0.5.0`, `0.5.1`). Active source lives in **`VectorTrack v4/`** and **`VectorTrackScript v4/`** on `main`.

Legacy prototypes (alpha, v0, v1, early TimeTracker scripts) are preserved on the [`archive`](https://github.com/Paragonlivedesign/VectorTrack/tree/archive) branch.

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

## 0.5.0 beta — changes

- Repository cleanup: legacy code on `archive` branch; `main` is current source only
- Open Files shows **project names**; **project numbers optional** on create
- Restored latest v4 feature work (session explorer, sync, session aggregator)
- Installer: `VectorTrack-0.5.0-Setup.exe`

Full history: [`VectorTrack v4/CHANGELOG.md`](VectorTrack%20v4/CHANGELOG.md)

---

## Quick start

**Desktop app** — build from [`VectorTrack v4/`](VectorTrack%20v4/) or run the packaged beta build if your tester package includes `VectorTrack-0.5.0-Setup.exe`.

**Vectorworks plug-in** — follow [`VectorTrackScript v4/README.md`](VectorTrackScript%20v4/README.md). Register the `.vsm` wrapper once in Plug-in Manager; Python sources ship in-repo.

---

## Repository layout (`main`)

| Path | Contents |
|------|----------|
| `VectorTrack v4/` | PyQt6 desktop app source |
| `VectorTrackScript v4/` | In-Vectorworks Python plug-in source |

Older code: check out the [`archive`](https://github.com/Paragonlivedesign/VectorTrack/tree/archive) branch.

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
