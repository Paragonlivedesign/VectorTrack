# Development guide

Internal documentation for building, testing, and publishing VectorTrack. Beta testers should use the [repository README](../README.md) and [GitHub Releases](https://github.com/Paragonlivedesign/VectorTrack/releases/latest) instead.

---

## Versioning

Pre-1.0 beta releases use **`0.5.x`** semver (e.g. `0.5.0`, `0.5.1`). Active source lives in **`VectorTrack 0.5/`** and **`VectorTrackScript 0.5/`** on `main`.

Git tags for releases follow **`v0.5.0-beta`**, **`v0.5.1-beta`**, etc.

Legacy prototypes (alpha, v0, v1, early TimeTracker scripts) are preserved on the [`archive`](https://github.com/Paragonlivedesign/VectorTrack/tree/archive) branch.

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

## Run from source

### Desktop app

```powershell
cd "VectorTrack 0.5"
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m vectortrack
```

Optional flags: `--portable` (store data next to the executable), `--debug`.

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

### Checklist

1. Update version strings if needed (`vectortrack/__init__.py`, `installer.iss`, plug-in version constants).
2. Update [`VectorTrack 0.5/CHANGELOG.md`](../VectorTrack%200.5/CHANGELOG.md).
3. Build desktop installer: `.\build.ps1 -WithInstaller` in `VectorTrack 0.5/`.
4. Build plug-in zip: `.\package_plugin.ps1` in `VectorTrackScript 0.5/`.
5. Commit and push source changes to `main` (do **not** commit `release/` binaries).
6. On GitHub: **Releases → Draft new release**.
   - Tag: `v0.5.0-beta` (match semver + `-beta` suffix)
   - Title: e.g. `VectorTrack 0.5.0 beta`
   - Release notes: copy the relevant section from CHANGELOG
   - Attach assets:
     - `VectorTrack-0.5.0-Setup.exe`
     - `VectorTrackScript_0.5.zip`
7. Publish the release.

For patch releases (e.g. 0.5.1), repeat with a new tag. Testers can reinstall from the new Release; uninstalling the old installer **keeps** user data in `%LOCALAPPDATA%\Paragon\VectorTrack\` unless they choose to remove it.

### gh CLI (optional)

```powershell
gh release create v0.5.0-beta `
  "VectorTrack 0.5/release/VectorTrack-0.5.0-Setup.exe" `
  "VectorTrackScript 0.5/VectorTrackScript_0.5.zip" `
  --title "VectorTrack 0.5.0 beta" `
  --notes-file "VectorTrack 0.5/CHANGELOG.md"
```

Adjust paths and notes as needed.

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
