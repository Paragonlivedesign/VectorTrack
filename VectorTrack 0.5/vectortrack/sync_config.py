"""Cross-machine log sync configuration for VectorTrack 0.5."""

from vectortrack_core.sync.config import (  # noqa: F401
    SyncConfig,
    default_machine_id,
    load_sync_config_from_paths_json,
    sync_config_from_mapping,
    sync_config_to_mapping,
)

from vectortrack.services.vw_identity import local_machine_id, resolve_sync_machine_id


def load_sync_config_from_settings(
    *,
    enabled: bool = False,
    folder: str = "",
    machine_id: str = "",
    machine_label: str = "",
    sync_on_refresh: bool = True,
) -> SyncConfig:
    return SyncConfig(
        enabled=enabled,
        folder=folder,
        machine_id=machine_id or default_machine_id(),
        machine_label=machine_label,
        sync_on_refresh=sync_on_refresh,
    )


def settings_keys_from_sync_config(sync_config: SyncConfig) -> dict[str, object]:
    return {
        "sync_enabled": sync_config.enabled,
        "sync_folder": sync_config.folder,
        "sync_machine_id": sync_config.machine_id or default_machine_id(),
        "sync_machine_label": sync_config.machine_label,
        "sync_on_refresh": sync_config.sync_on_refresh,
    }
