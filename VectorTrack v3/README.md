# VectorTrack v4

Professional time tracking for Vectorworks — standalone Windows desktop app.

**Version:** 4.0.0

## Features

- Automatic detection of open Vectorworks files (multi-file)
- Idle detection via keyboard/mouse activity
- Per-file hourly rates and idle timeouts
- SQLite session storage
- PDF reports (per-file and master)
- Dark/light themes

## Requirements

- Windows 10+
- Python 3.10+ (development only; use the built `.exe` for daily use)

## Development setup

```powershell
cd "VectorTrack v3"
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m vectortrack
```

## Tests

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
.\.venv\Scripts\python -m pytest tests\ -q
```

## Build executable

```powershell
# Build executable (outputs to C:\Temp\VectorTrackBuild to avoid Google Drive locks)
.\build.ps1

# Build Windows installer (requires Inno Setup 6)
.\build_installer.ps1
# Or both:
.\build.ps1 -WithInstaller
```

Outputs:
- `C:\Temp\VectorTrackBuild\VectorTrack\VectorTrack.exe` (portable folder build)
- `dist\installer\VectorTrack-v4-Setup.exe` (after Inno Setup compile)

### Installing on a new computer

1. **Recommended:** Install [Inno Setup 6](https://jrsoftware.org/isdl.php), run `.\build_installer.ps1`, then copy `VectorTrack-v4-Setup.exe` to the target PC and run it. The installer adds Start Menu shortcuts, optional desktop icon, and uninstall support.
2. **Without installer:** Copy the entire `VectorTrack` folder from `C:\Temp\VectorTrackBuild\VectorTrack` (or `_2 Beta Testing\VectorTrack v4\release\`) to the new PC and run `VectorTrack.exe`. Data is stored under `%LOCALAPPDATA%\Paragon\VectorTrack\`.

## v4.0 scope

- MainWindow smoke tests enabled in CI
- PyInstaller packaging with app icon and explicit service/db hidden imports
- Inno Setup installer (`installer.iss`) with optional desktop icon and uninstall data retention prompt
- Build chain scripts for executable + installer shipping

## Deferred to v4.1+

- Project version merging across file revisions
- Cloud sync / payment infrastructure
- Full GUI test coverage

## Related

In-Vectorworks log-based summary: see `VectorTrackScript v3/` in the parent folder.

## Beta handoff copy

After validating a build, copy this folder to:

`..\_2 Beta Testing\VectorTrack v4\`
