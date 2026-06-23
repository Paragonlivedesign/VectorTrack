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

Pre-1.0 beta releases use **`0.5.x`** semver (e.g. `0.5.0`, `0.5.1`). Active source lives in **`VectorTrack 0.5/`** and **`VectorTrackScript 0.5/`** on `main`.

Legacy prototypes (alpha, v0, v1, early TimeTracker scripts) are preserved on the [`archive`](https://github.com/Paragonlivedesign/VectorTrack/tree/archive) branch.

---

## Products

Two installs, same problem domain. Use either one or both.

| Product | Install target | Docs |
|---------|----------------|------|
| **VectorTrack** | Windows 10+ desktop | [`VectorTrack 0.5/README.md`](VectorTrack%200.5/README.md) |
| **VectorTrackScript** | Vectorworks plug-in (2025 / 2026 tested) | [`VectorTrackScript 0.5/README.md`](VectorTrackScript%200.5/README.md) |

**VectorTrack** watches open Vectorworks documents, tracks active vs idle time, stores sessions locally, and exports PDF reports.

**VectorTrackScript** opens a summary dialog inside Vectorworks for the file you have open — sessions, rates, budget, and copy-to-clipboard for billing.

Neither product requires the other.

---

## 0.5.0 beta — changes

- Repository cleanup: legacy code on `archive` branch; `main` is current source only
- Open Files shows **project names**; **project numbers optional** on create
- Restored latest v4 feature work (session explorer, sync, session aggregator)
- Installer: `VectorTrack-0.5.0-Setup.exe`

Full history: [`VectorTrack 0.5/CHANGELOG.md`](VectorTrack%200.5/CHANGELOG.md)

---

## Quick start

**Desktop app** — build from [`VectorTrack 0.5/`](VectorTrack%200.5/) or download `VectorTrack 0.5/release/VectorTrack-0.5.0-Setup.exe`.

**Vectorworks plug-in** — follow [`VectorTrackScript 0.5/README.md`](VectorTrackScript%200.5/README.md). Register the `.vsm` wrapper once in Plug-in Manager; Python sources ship in-repo.

---

## Repository layout (`main`)

| Path | Contents |
|------|----------|
| `VectorTrack 0.5/` | PyQt6 desktop app source |
| `VectorTrack 0.5/release/` | Portable `VectorTrack.exe` + `VectorTrack-0.5.0-Setup.exe` |
| `VectorTrackScript 0.5/` | In-Vectorworks Python plug-in source |

Older code: check out the [`archive`](https://github.com/Paragonlivedesign/VectorTrack/tree/archive) branch.

---

## Requirements

| Component | Requirement |
|-----------|-------------|
| VectorTrack | Windows 10 or later |
| VectorTrack (dev) | Python 3.10+, dependencies in `VectorTrack 0.5/requirements.txt` |
| VectorTrackScript | Vectorworks with Python scripting (2025 / 2026 verified) |

---

## Build (developers)

```powershell
# Desktop app
cd "VectorTrack 0.5"
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m vectortrack

# Package desktop app + installer
.\build.ps1 -WithInstaller

# Vectorworks plug-in zip
cd "..\VectorTrackScript 0.5"
.\package_plugin.ps1
```

---

## License

See [`VectorTrack 0.5/EULA.md`](VectorTrack%200.5/EULA.md). Beta builds may include licensing hooks that are disabled in current test builds.
