"""Typed application settings backed by QSettings."""

from __future__ import annotations

from dataclasses import dataclass, fields

from PyQt6.QtCore import QSettings

from vectortrack import config


@dataclass
class AppSettings:
    default_hourly_rate: float = config.DEFAULT_HOURLY_RATE
    default_idle_timeout: int = config.DEFAULT_IDLE_MINUTES
    idle_pause_enabled: bool = config.DEFAULT_IDLE_PAUSE_ENABLED
    idle_bypass_mode: str = config.DEFAULT_IDLE_BYPASS_MODE
    auto_track_enabled: bool = True
    import_vw_log_history: bool = True
    vw_log_merge_years: bool = True
    vw_log_path: str = ""
    vectorworks_path: str = ""
    sync_enabled: bool = False
    sync_folder: str = ""
    sync_machine_id: str = ""
    sync_machine_label: str = ""
    sync_on_refresh: bool = True
    dark_mode_enabled: bool = False
    minimize_to_tray: bool = True
    notifications_enabled: bool = True
    global_hotkeys_enabled: bool = True
    end_of_day_hour: int = 18
    wizard_completed: bool = False


class SettingsStore:
    ORG = "Paragon"
    APP = "VectorTrack"

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings(self.ORG, self.APP)

    @property
    def qsettings(self) -> QSettings:
        return self._settings

    def load(self) -> AppSettings:
        loaded = AppSettings()
        for field in fields(AppSettings):
            default = getattr(loaded, field.name)
            value = self._settings.value(field.name, default)
            if isinstance(default, bool):
                setattr(
                    loaded,
                    field.name,
                    self._settings.value(field.name, default, type=bool),
                )
            elif isinstance(default, int):
                setattr(loaded, field.name, int(value))
            elif isinstance(default, float):
                setattr(loaded, field.name, float(value))
            else:
                setattr(loaded, field.name, str(value) if value is not None else default)
        return loaded

    def save(self, app_settings: AppSettings) -> None:
        for field in fields(AppSettings):
            self._settings.setValue(field.name, getattr(app_settings, field.name))
        self._settings.sync()

    def load_file_project_overrides(self) -> dict[str, str]:
        import json

        raw = self._settings.value("file_project_overrides", "{}", type=str)
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        return {}

    def save_file_project_overrides(self, overrides: dict[str, str]) -> None:
        import json

        self._settings.setValue("file_project_overrides", json.dumps(overrides))
