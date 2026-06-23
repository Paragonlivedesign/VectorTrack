# VectorTrack

Windows desktop time tracker for Vectorworks.

| | |
|---|---|
| **Version** | 0.5.0 beta |
| **Platform** | Windows 10+ |
| **Publisher** | Paragon Live Design |

Source tree for the standalone app. See the [repository README](../README.md) for release notes.

---

## Development

Requires Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m vectortrack
```

**Tests**

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
.\.venv\Scripts\python -m pytest tests\ -q
```

**Package**

```powershell
.\build.ps1                  # VectorTrack.exe (writes to C:\Temp\VectorTrackBuild)
.\build.ps1 -WithInstaller   # exe + VectorTrack-0.5.0-Setup.exe
```

Portable build: `C:\Temp\VectorTrackBuild\VectorTrack\VectorTrack.exe`  
Installer: `dist\installer\VectorTrack-0.5.0-Setup.exe`

---

## Cross-machine log sync

**Edit → Settings** → enable sync, choose a cloud-synced folder, set a unique **Machine ID** per computer. Off by default.

---

## Related

In-Vectorworks plug-in: [`VectorTrackScript v4/`](../VectorTrackScript%20v4/)  
Changelog: [`CHANGELOG.md`](CHANGELOG.md)
