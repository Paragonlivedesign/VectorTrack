# VectorTrackScript

Vectorworks menu command — time summary from `Vectorworks Log.txt` for the document currently open.

| | |
|---|---|
| **Version** | 0.5.0 beta |
| **Tested with** | Vectorworks 2025 / 2026 |
| **Publisher** | Paragon Live Design |

Source tree for the in-Vectorworks plug-in. See the [repository README](../README.md) for release notes.

---

## Install

**From zip**

```powershell
.\package_plugin.ps1
```

Install via **Tools → Plug-ins → Plug-in Manager → Third-party Plug-ins → Install**.

**Manual copy** — all `.py` files to:

```
%APPDATA%\Nemetschek\Vectorworks\<year>\Plug-ins\VectorTrackScript 0.5\
```

Register the `.vsm` once in Plug-in Manager (paste [`VSM_WRAPPER.py`](VSM_WRAPPER.py); menu command name must be **`VectorTrackScript 0.5`**).

---

## 0.5.0 beta

Aligned with VectorTrack desktop **0.5.0 beta**. See [`VectorTrack 0.5/CHANGELOG.md`](../VectorTrack%200.5/CHANGELOG.md).

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

## Tests

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -m pytest tests\ -q
```

---

## Related

Standalone desktop app: [`VectorTrack 0.5/`](../VectorTrack%200.5/)
