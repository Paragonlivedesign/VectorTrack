"""Tests for tray icon composition."""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QApplication

from vectortrack.ui.app_icon import app_icon, tray_icon


@pytest.fixture
def app():
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    yield instance
    instance.processEvents()


def test_tray_icon_builds_for_each_status(app):
    for status in ("inactive", "tracking", "paused", "idle"):
        icon = tray_icon(status=status)
        assert not icon.isNull()
        pixmap = icon.pixmap(32, 32)
        assert not pixmap.isNull()


def test_tray_tracking_icon_differs_from_paused(app):
    tracking = tray_icon(status="tracking").pixmap(32, 32)
    paused = tray_icon(status="paused").pixmap(32, 32)
    assert not tracking.isNull()
    assert tracking.toImage() != paused.toImage()


def test_app_icon_is_available(app):
    assert not app_icon().isNull()
