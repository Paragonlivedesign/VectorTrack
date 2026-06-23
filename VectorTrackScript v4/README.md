# VectorTrackScript

Vectorworks menu command — time summary from `Vectorworks Log.txt` for the document currently open.

| | |
|---|---|
| **Version** | 0.4.0 beta |
| **Tested with** | Vectorworks 2025 / 2026 |
| **Publisher** | Paragon Live Design |

Source tree for the in-Vectorworks plug-in. See the [repository README](../README.md) for 0.4 beta release notes.

---

## Install

**From zip**

```powershell
.\package_plugin.ps1
```

Install via **Tools → Plug-ins → Plug-in Manager → Third-party Plug-ins → Install**.

**Manual copy** — all `.py` files to:

```
%APPDATA%\Nemetschek\Vectorworks\<year>\Plug-ins\VectorTrackScript v4\
```

Register the `.vsm` once in Plug-in Manager (paste [`VSM_WRAPPER.py`](VSM_WRAPPER.py); menu command name must be **`VectorTrackScript v4`**).

---

## 0.4.0 beta — changes

- Client, budget, and trust-note fields in the summary dialog
- Alias-aware parsing for renamed / save-as files
- Copy-to-clipboard for billing
- Cross-machine log sync (**Sync...** and `paths.json`)
- Per-project rates in `rates.json`; metadata in `paths.json`

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

Standalone desktop app: [`VectorTrack v4/`](../VectorTrack%20v4/)
