"""SettingsStore QSettings coercion tests."""

from __future__ import annotations

from PyQt6.QtCore import QSettings

from vectortrack.settings_store import SettingsStore


def test_load_bool_from_qsettings_string_false(tmp_path) -> None:
    ini = tmp_path / "settings.ini"
    settings = QSettings(str(ini), QSettings.Format.IniFormat)
    settings.setValue("dark_mode_enabled", "false")
    store = SettingsStore(settings)
    loaded = store.load()
    assert loaded.dark_mode_enabled is False


def test_load_bool_from_qsettings_string_true(tmp_path) -> None:
    ini = tmp_path / "settings.ini"
    settings = QSettings(str(ini), QSettings.Format.IniFormat)
    settings.setValue("dark_mode_enabled", "true")
    store = SettingsStore(settings)
    loaded = store.load()
    assert loaded.dark_mode_enabled is True
