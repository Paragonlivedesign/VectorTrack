# Development guide

Internal documentation for building, testing, and publishing VectorTrack. Beta testers should use the [repository README](../README.md) and [GitHub Releases](https://github.com/Paragonlivedesign/VectorTrack/releases/latest) instead.

---

## Versioning and releases

SemVer, branch model, version bump files, and the step-by-step release checklist are in **[`DEPLOYMENT.md`](DEPLOYMENT.md)**.

Active source lives in **`VectorTrack 0.5/`** and **`VectorTrackScript 0.5/`** on `main`. Legacy prototypes are on the [`archive`](https://github.com/Paragonlivedesign/VectorTrack/tree/archive) branch.

Version history: [`VectorTrack 0.5/CHANGELOG.md`](../VectorTrack%200.5/CHANGELOG.md)

---

## Repository layout (`main`)

| Path | Contents |
|------|----------|
| `VectorTrack 0.5/` | PyQt6 desktop app source |
| `VectorTrack 0.5/release/` | Local build output (gitignored) — portable exe + installer copies |
| `VectorTrackScript 0.5/` | In-Vectorworks Python plug-in source |
| `docs/` | Developer and user documentation |

Older code: check out the [`archive`](https://github.com/Paragonlivedesign/VectorTrack/tree/archive) branch.

---

## Requirements

| Component | Requirement |
|-----------|-------------|
| VectorTrack (runtime) | Windows 10 or later |
| VectorTrack (dev) | Python 3.10+, dependencies in `VectorTrack 0.5/requirements.txt` |
| VectorTrack (packaging) | PyInstaller; Inno Setup 6 for the Windows installer |
| VectorTrackScript | Vectorworks with Python scripting (2025 / 2026 verified) |

---

## Daily development (no reinstall)

For your own work on `main`, **run from source**. You only need to rebuild the installer when publishing a beta for testers.

| Workflow | When to use | Command |
|----------|-------------|---------|
| **Dev (recommended)** | Every code change while you develop | `.\dev.ps1` in `VectorTrack 0.5/` |
| **Installed app** | Testing the real installer experience | Run `VectorTrack-0.5.0-Setup.exe` once; use Start Menu after that |
| **Release build** | Shipping to GitHub Releases / testers | `.\build.ps1 -WithInstaller` |

### Quick start

```powershell
cd "VectorTrack 0.5"
.\dev.ps1
```

First run creates `.venv/` and installs dependencies. After you change Python code, **close VectorTrack and run `.\dev.ps1` again** — no rebuild, no reinstall.

**Shared data:** dev and installed builds both use `%LOCALAPPDATA%\Paragon\VectorTrack\` (sessions, settings, logs, reports). Your database and preferences carry over between dev and installed runs.

**Single instance:** quit the installed app (system tray) before starting `.\dev.ps1`, or the new session will exit immediately.

**Portable dev data** (optional, isolated from installed app):

```powershell
.\dev.ps1 --portable
```

Creates `VectorTrack 0.5/data/` next to the source tree instead of using AppData.

---

## Run from source (manual)

### Desktop app

```powershell
cd "VectorTrack 0.5"
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m vectortrack
```

Optional flags: `--portable` (store data next to the source tree), `--debug`.

Or use [`dev.ps1`](../VectorTrack%200.5/dev.ps1) which wraps the above.

### Vectorworks plug-in

Copy sources to `%APPDATA%\Nemetschek\Vectorworks\<year>\Plug-ins\VectorTrackScript 0.5\` or use the packaged zip. Register the `.vsm` wrapper once in Plug-in Manager (menu command name must be **`VectorTrackScript 0.5`**). See [`VectorTrackScript 0.5/README.md`](../VectorTrackScript%200.5/README.md).

---

## Tests

**Desktop app**

```powershell
cd "VectorTrack 0.5"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
.\.venv\Scripts\python -m pytest tests\ -q
```

**Plug-in**

```powershell
cd "VectorTrackScript 0.5"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -m pytest tests\ -q
```

---

## Build and package

### Desktop app + installer

```powershell
cd "VectorTrack 0.5"
.\build.ps1                  # portable exe → release/ (and C:\Temp\VectorTrackBuild)
.\build.ps1 -WithInstaller   # exe + VectorTrack-0.5.0-Setup.exe
```

Outputs:

| Artifact | Path |
|----------|------|
| Portable build | `VectorTrack 0.5/release/VectorTrack.exe` (+ `_internal/`) |
| Installer | `VectorTrack 0.5/dist/installer/VectorTrack-0.5.0-Setup.exe` |
| Release copy | `VectorTrack 0.5/release/VectorTrack-0.5.0-Setup.exe` |

Inno Setup script: [`installer.iss`](../VectorTrack%200.5/installer.iss). PyInstaller spec: [`build.spec`](../VectorTrack%200.5/build.spec).

### Vectorworks plug-in zip

```powershell
cd "VectorTrackScript 0.5"
.\package_plugin.ps1
```

Produces `VectorTrackScript_0.5.zip` in that folder. Copy the generated `.vsm` from Vectorworks into the script folder before packaging if distributing a ready-to-install zip.

---

## Publishing a GitHub Release

`main` is living source. Testers should install from **tagged Releases**, not from files on the branch.

See **[`DEPLOYMENT.md`](DEPLOYMENT.md)** for the full release workflow (version bumps, build order, smoke test, tagging, and optional `gh` CLI).

---

## Data paths (reference)

| Mode | Program files | User data |
|------|---------------|-----------|
| Installed (default) | `%ProgramFiles%\Paragon Live Design\VectorTrack\` | `%LOCALAPPDATA%\Paragon\VectorTrack\` |
| Portable mode | N/A (run from chosen folder) | `data/` next to `VectorTrack.exe` |

User data includes `vectortrack.db`, settings, backups, and related JSON files. Log files are stored under `{data_dir}/logs/`.

---

## License

See [`VectorTrack 0.5/EULA.md`](../VectorTrack%200.5/EULA.md). Beta builds may include licensing hooks that are disabled in current test builds (`ENFORCE_LICENSING = False`).
