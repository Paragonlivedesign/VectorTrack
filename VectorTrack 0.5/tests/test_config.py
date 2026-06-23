"""
Tests for v4 configuration path helpers.
"""

from __future__ import annotations

import json
from pathlib import Path

from vectortrack import config


def test_resolve_data_dir_uses_env_override(monkeypatch, tmp_path):
    custom_dir = tmp_path / "custom-data"
    monkeypatch.setenv(config.ENV_DATA_DIR, str(custom_dir))

    resolved = config.resolve_data_dir()

    assert resolved == custom_dir
    assert resolved.exists()
    assert resolved.is_dir()


def test_db_path_and_legacy_path(monkeypatch, tmp_path):
    monkeypatch.setenv(config.ENV_DATA_DIR, str(tmp_path))

    assert config.db_path() == Path(tmp_path) / config.DEFAULT_DB_FILENAME
    assert config.legacy_db_path() == Path(tmp_path) / config.LEGACY_DB_FILENAME


def test_resolve_data_dir_prefers_portable(monkeypatch, tmp_path):
    monkeypatch.setenv(config.ENV_DATA_DIR, str(tmp_path / "env-data"))
    monkeypatch.setattr(config, "_portable_mode", True)
    monkeypatch.setattr(config, "_exe_dir", lambda: tmp_path)

    resolved = config.resolve_data_dir()
    assert resolved == tmp_path / "data"


def test_logs_dir_lives_under_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv(config.ENV_DATA_DIR, str(tmp_path))

    resolved = config.logs_dir()

    assert resolved == tmp_path / "logs"
    assert resolved.is_dir()


def test_write_paths_json(monkeypatch, tmp_path):
    monkeypatch.setenv(config.ENV_DATA_DIR, str(tmp_path))
    target = config.write_paths_json(extra={"custom": "ok"})
    assert target == tmp_path / "paths.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["data_dir"] == str(tmp_path)
    assert payload["db_path"].endswith(config.DEFAULT_DB_FILENAME)
    assert payload["custom"] == "ok"
