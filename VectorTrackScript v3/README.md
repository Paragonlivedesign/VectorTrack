# VectorTrackScript v4

In-Vectorworks time tracking summary from `Vectorworks Log.txt` for the **currently open file**.

**Version:** 4.0.0  
**Tested with:** Vectorworks 2025 / 2026 (log path auto-detected via `vs.GetVersion()`)

## Features

- Menu command plugin (`.vsm`) — not a palette script
- Auto-finds `Vectorworks Log.txt` for the running VW year (fallback scan 2020–2030)
- Summary dialog: project, client, hourly rate, budget remaining, trust note, session list, totals
- Alias-aware parsing with save-as continuity across renamed project files
- Copy-to-clipboard button for quick invoice/email paste
- Remembers hourly rate per project filename in `rates.json`
- Optional `paths.json` for aliases and project metadata
- No dependency on the VectorTrack standalone desktop app

## One-time setup (create the .vsm)

The `.vsm` file is binary and **must** be created in Vectorworks:

1. **Tools → Plug-ins → Plug-in Manager → Custom Plug-ins → New**
2. Type: **Menu Command**, Language: **Python Script**
3. Name: **`VectorTrackScript v4`** (must match install folder name exactly)
4. Category: e.g. **Miscellaneous**
5. **Edit Script** — paste contents of [`VSM_WRAPPER.py`](VSM_WRAPPER.py)
6. Adjust `VW_YEAR = '2026'` in the wrapper if needed
7. Save — Vectorworks creates the `.vsm` in your user Plug-ins folder
8. Copy `VectorTrackScript v3.vsm` from  
   `%APPDATA%\Nemetschek\Vectorworks\<year>\Plug-ins\`  
   into this development folder
9. **Tools → Workspaces → Edit Current Workspace** — add the command to a menu

## Development install (without zip)

Copy these files into:

```
%APPDATA%\Nemetschek\Vectorworks\<year>\Plug-ins\VectorTrackScript v4\
```

Files: `vectortrackscript_main.py`, `vectortrack_log.py`, `vectortrack_rates.py`, `vectortrack_dialog.py`, `vectortrack_config.py`

## Package for distribution

```powershell
.\package_plugin.ps1
```

Install the zip via **Plug-in Manager → Third-party Plug-ins → Install**.

## Files

| File | Purpose |
|------|---------|
| `VectorTrackScript v3.vsm` | VW menu command wrapper (create in VW, copy here) |
| `VSM_WRAPPER.py` | Script text to paste into Plug-in Manager |
| `vectortrackscript_main.py` | Entry point / error handling |
| `vectortrack_log.py` | Log discovery and session parsing |
| `vectortrack_config.py` | `paths.json` loader + alias/project metadata helpers |
| `vectortrack_rates.py` | Per-project rate persistence |
| `vectortrack_dialog.py` | CreateLayout summary UI |
| `package_plugin.ps1` | Build install zip |
| `tests/` | Unit tests (log parser + rates, no VW required) |

## Beta handoff copy

After validating a build, copy this folder to:

`..\_2 Beta Testing\VectorTrackScript v4\`

## Credits

PLD (Paragon Live Design) — Cody@Paragonlivedesign.com
