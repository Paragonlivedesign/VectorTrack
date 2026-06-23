"""
Sync settings dialog for VectorTrackScript 0.5 (CreateLayout).
"""

from __future__ import annotations

import vs

from vectortrack_config import SyncConfig, default_machine_id, load_sync_config, save_sync_config

# Sync dialog item IDs
kSyncChkEnabled = 101
kSyncLabelFolder = 102
kSyncEditFolder = 103
kSyncBtnBrowse = 104
kSyncLabelMachineId = 105
kSyncEditMachineId = 106
kSyncLabelMachineLabel = 107
kSyncEditMachineLabel = 108
kSyncChkOnRefresh = 109

_sync_dialog = None
_sync_vw_year = 2026


def _read_sync_config_from_dialog() -> SyncConfig:
    return SyncConfig(
        enabled=vs.GetBooleanItem(_sync_dialog, kSyncChkEnabled),
        folder=vs.GetItemText(_sync_dialog, kSyncEditFolder).strip(),
        machine_id=vs.GetItemText(_sync_dialog, kSyncEditMachineId).strip() or default_machine_id(),
        machine_label=vs.GetItemText(_sync_dialog, kSyncEditMachineLabel).strip(),
        sync_on_refresh=vs.GetBooleanItem(_sync_dialog, kSyncChkOnRefresh),
    )


def _populate_sync_dialog(sync_config: SyncConfig) -> None:
    vs.SetBooleanItem(_sync_dialog, kSyncChkEnabled, sync_config.enabled)
    vs.SetItemText(_sync_dialog, kSyncEditFolder, sync_config.folder)
    vs.SetItemText(
        _sync_dialog,
        kSyncEditMachineId,
        sync_config.machine_id or default_machine_id(),
    )
    vs.SetItemText(_sync_dialog, kSyncEditMachineLabel, sync_config.machine_label)
    vs.SetBooleanItem(_sync_dialog, kSyncChkOnRefresh, sync_config.sync_on_refresh)


def _create_sync_dialog(sync_config: SyncConfig):
    global _sync_dialog
    _sync_dialog = vs.CreateLayout(
        'Cross-Machine Log Sync',
        True,
        'Save',
        'Cancel',
    )

    vs.CreateCheckBox(_sync_dialog, kSyncChkEnabled, 'Enable cross-machine log sync')
    vs.CreateStaticText(_sync_dialog, kSyncLabelFolder, 'Sync folder:', 14)
    vs.CreateEditText(_sync_dialog, kSyncEditFolder, sync_config.folder, 56)
    vs.CreatePushButton(_sync_dialog, kSyncBtnBrowse, 'Browse...')
    vs.CreateStaticText(_sync_dialog, kSyncLabelMachineId, 'Machine ID:', 14)
    vs.CreateEditText(
        _sync_dialog,
        kSyncEditMachineId,
        sync_config.machine_id or default_machine_id(),
        32,
    )
    vs.CreateStaticText(_sync_dialog, kSyncLabelMachineLabel, 'Machine label:', 14)
    vs.CreateEditText(_sync_dialog, kSyncEditMachineLabel, sync_config.machine_label, 32)
    vs.CreateCheckBox(_sync_dialog, kSyncChkOnRefresh, 'Sync on Refresh')

    vs.SetFirstLayoutItem(_sync_dialog, kSyncChkEnabled)
    vs.SetBelowItem(_sync_dialog, kSyncChkEnabled, kSyncLabelFolder, 0, 8)
    vs.SetRightItem(_sync_dialog, kSyncLabelFolder, kSyncEditFolder, 0, 0)
    vs.SetRightItem(_sync_dialog, kSyncEditFolder, kSyncBtnBrowse, 8, 0)
    vs.SetBelowItem(_sync_dialog, kSyncLabelFolder, kSyncLabelMachineId, 0, 0)
    vs.SetRightItem(_sync_dialog, kSyncLabelMachineId, kSyncEditMachineId, 0, 0)
    vs.SetBelowItem(_sync_dialog, kSyncLabelMachineId, kSyncLabelMachineLabel, 0, 0)
    vs.SetRightItem(_sync_dialog, kSyncLabelMachineLabel, kSyncEditMachineLabel, 0, 0)
    vs.SetBelowItem(_sync_dialog, kSyncLabelMachineLabel, kSyncChkOnRefresh, 0, 8)

    return _sync_dialog


def _sync_dialog_handler(item, _data):
    if item == kSyncBtnBrowse:
        result, folder_path = vs.GetFolder('Select cloud sync folder (Google Drive, Dropbox, etc.)')
        if result and folder_path:
            vs.SetItemText(_sync_dialog, kSyncEditFolder, folder_path)
    elif item == setup:
        _populate_sync_dialog(load_sync_config(_sync_vw_year))


setup = 2
ok = 1
cancel = 0


def show_sync_settings(vw_year: int) -> SyncConfig | None:
    """
    Show sync settings dialog.
    Returns updated SyncConfig on Save, or None if cancelled.
    """
    global _sync_vw_year
    _sync_vw_year = vw_year
    initial = load_sync_config(vw_year)
    dialog = _create_sync_dialog(initial)
    _populate_sync_dialog(initial)
    result = vs.RunLayoutDialog(dialog, _sync_dialog_handler)
    if result != ok:
        return None
    updated = _read_sync_config_from_dialog()
    save_sync_config(vw_year, updated)
    return updated
