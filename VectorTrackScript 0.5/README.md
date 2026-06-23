# VectorTrackScript

Vectorworks menu command — time summary from `Vectorworks Log.txt` for the document currently open.

| | |
|---|---|
| **Version** | 0.5.4 beta |
| **Tested with** | Vectorworks 2025 / 2026 |
| **Publisher** | Paragon Live Design |

**Download:** get **`VectorTrackScript_0.5.zip`** from **[GitHub Releases](https://github.com/Paragonlivedesign/VectorTrack/releases/latest)**.

**Build from source:** see [`docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md).

---

## Install

**From release zip**

1. Download `VectorTrackScript_0.5.zip` from [Latest Release](https://github.com/Paragonlivedesign/VectorTrack/releases/latest).
2. In Vectorworks: **Tools → Plug-ins → Plug-in Manager → Third-party Plug-ins → Install…** and select the zip.

**From source (developers)**

```powershell
.\package_plugin.ps1
```

Then install the generated zip via Plug-in Manager.

**Manual copy** — all `.py` files to:

```
%APPDATA%\Nemetschek\Vectorworks\<year>\Plug-ins\VectorTrackScript 0.5\
```

Register the `.vsm` once in Plug-in Manager (paste [`VSM_WRAPPER.py`](VSM_WRAPPER.py); menu command name must be **`VectorTrackScript 0.5`**).

---

## Cross-machine log sync

Optional, off by default. Enable in the **Sync...** dialog or set `sync` in `paths.json`:

```json
{
  "sync": {
    "enabled": true,
    "folder": "G:/My Drive/VectorTrack/logs",
    "machine_id": "office-desktop",
    "machine_label": "Office Desktop",
    "sync_on_refresh": true
  }
}
```

---

## Related

- Standalone desktop app: [`VectorTrack 0.5/`](../VectorTrack%200.5/) · [download installer](https://github.com/Paragonlivedesign/VectorTrack/releases/latest)
- Changelog: [`VectorTrack 0.5/CHANGELOG.md`](../VectorTrack%200.5/CHANGELOG.md)
