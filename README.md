# VectorTrack

Time tracking built around your Vectorworks workflow — a Windows desktop app and an optional in-app menu command for session summaries and billing.

| | |
|---|---|
| **Version** | 0.5.1 beta |
| **Platform** | Windows 10+ · Vectorworks 2025 / 2026 (plug-in) |
| **Publisher** | [Paragon Live Design](https://paragonlivedesign.com) |
| **Support** | Cody@Paragonlivedesign.com |

> **Beta software.** Builds are for invited testers. Source on `main` updates continuously; **install from a tagged [GitHub Release](https://github.com/Paragonlivedesign/VectorTrack/releases/latest)** for a tested snapshot. Windows may show a SmartScreen warning because the installer is not code-signed yet — choose **More info → Run anyway**. Expect rough edges; report issues to support.

---

## Download

**[Download latest beta (Windows installer)](https://github.com/Paragonlivedesign/VectorTrack/releases/latest)**

Each release includes:

| File | What it is |
|------|------------|
| **`VectorTrack-0.5.1-Setup.exe`** | **Recommended.** Installs the desktop app with Start Menu shortcut and uninstaller. |
| **`VectorTrackScript_0.5.zip`** | Optional Vectorworks plug-in — install through Plug-in Manager. |

You do not need both products, but they work well together.

**What's new:** [`VectorTrack 0.5/CHANGELOG.md`](VectorTrack%200.5/CHANGELOG.md)

---

## What you get

| Product | Where it runs | Best for |
|---------|---------------|----------|
| **VectorTrack** | Windows desktop (background + system tray) | Automatic tracking of open Vectorworks files, idle time, projects, sessions, and PDF reports |
| **VectorTrackScript** | Inside Vectorworks (menu command) | Quick time summary for the file you have open — sessions, rates, budget, copy-to-clipboard |

Neither product requires the other.

---

## Features (0.5 beta)

- **Automatic tracking** — detects open Vectorworks documents and distinguishes active vs idle time
- **Multi-file support** — per-file rates and settings when several drawings are open
- **Projects** — organize work by project name (project numbers are optional)
- **Session explorer** — browse, edit, and aggregate recorded sessions
- **PDF reports** — export billing-ready summaries
- **Light / dark theme**
- **Optional cross-machine sync** — merge logs through a cloud-synced folder you choose (Google Drive, Dropbox, etc.); off by default
- **VectorTrackScript** — in-Vectorworks dialog for the current document’s log data

---

## Install — VectorTrack (desktop)

1. Download **`VectorTrack-0.5.1-Setup.exe`** from [Latest Release](https://github.com/Paragonlivedesign/VectorTrack/releases/latest).
2. Run the installer. If SmartScreen appears, click **More info**, then **Run anyway**.
3. Optionally check **Create a desktop shortcut** during setup.
4. Launch **VectorTrack** from the Start Menu. The app runs in the background and appears in the system tray.

On first launch the app creates your local data folder and begins monitoring when Vectorworks is in use.

---

## Install — VectorTrackScript (Vectorworks)

1. Download **`VectorTrackScript_0.5.zip`** from the same Release page.
2. In Vectorworks: **Tools → Plug-ins → Plug-in Manager → Third-party Plug-ins → Install…** and select the zip.
3. If installing manually, copy all files to:
   ```
   %APPDATA%\Nemetschek\Vectorworks\<year>\Plug-ins\VectorTrackScript 0.5\
   ```
4. Register the menu command once in Plug-in Manager if prompted (paste `VSM_WRAPPER.py`; name must be **`VectorTrackScript 0.5`**).

More detail: [`VectorTrackScript 0.5/README.md`](VectorTrackScript%200.5/README.md)

---

## Your data

The installer puts the **program** in Program Files. Your **sessions, settings, and backups** are stored separately so they survive app updates.

| What | Typical location |
|------|------------------|
| Installed app | `C:\Program Files\Paragon Live Design\VectorTrack\` |
| Sessions database, settings, backups | `%LOCALAPPDATA%\Paragon\VectorTrack\` |
| Vectorworks plug-in | `%APPDATA%\Nemetschek\Vectorworks\<year>\Plug-ins\VectorTrackScript 0.5\` |

**Uninstalling** VectorTrack removes the program from Program Files. The uninstaller asks whether to **keep or remove** your data folder — choose **Yes** to keep sessions and settings.

**Portable mode** (advanced): enable **Portable mode** in **Edit → Settings**, or launch with `--portable`, to store data in a `data/` folder next to the executable instead of AppData. Most testers should use the normal installer and leave portable mode off.

**Log files:** `%LOCALAPPDATA%\Paragon\VectorTrack\logs\vectortrack.log`

---

## Updating

When a new beta is published:

1. Check [Releases](https://github.com/Paragonlivedesign/VectorTrack/releases) or the [changelog](VectorTrack%200.5/CHANGELOG.md).
2. Download and run the new **Setup.exe** (you can install over the previous version).
3. Your data in `%LOCALAPPDATA%\Paragon\VectorTrack\` is preserved unless you explicitly remove it during uninstall.

For the Vectorworks plug-in, reinstall the new zip when noted in the release notes.

---

## Support and feedback

Email **Cody@Paragonlivedesign.com** with:

- VectorTrack version ( **Help → About** )
- Windows version
- What you expected vs what happened
- Relevant log excerpt from `%LOCALAPPDATA%\Paragon\VectorTrack\logs\vectortrack.log` if applicable

---

## For developers

Build and test: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md). Versioning, branches, and publishing betas: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## License

See [`VectorTrack 0.5/EULA.md`](VectorTrack%200.5/EULA.md).
