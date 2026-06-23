"""Tests for idle timeout settings loading."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from vectortrack.app import idle_timeout_seconds_from_settings


@pytest.fixture
def app():
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    yield instance


def test_idle_timeout_seconds_from_settings_reads_qsettings(app):
    settings = QSettings("Paragon", "VectorTrack")
    settings.setValue("default_idle_timeout", 12)
    app.setProperty("vectortrack_idle_seconds", None)

    assert idle_timeout_seconds_from_settings() == 12 * 60


def test_idle_timeout_seconds_from_settings_prefers_test_override(app):
    settings = QSettings("Paragon", "VectorTrack")
    settings.setValue("default_idle_timeout", 12)
    app.setProperty("vectortrack_idle_seconds", 90)

    assert idle_timeout_seconds_from_settings() == 90
    app.setProperty("vectortrack_idle_seconds", None)
