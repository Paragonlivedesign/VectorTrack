"""
Shared pytest configuration for VectorTrack 0.5.
"""

import os

import pytest

# Must be set before any QApplication is created (import-time, not fixture-time).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def vectortrack_test_mode(monkeypatch):
    """Avoid starting real input listeners during tests."""
    monkeypatch.setenv("VECTORTRACK_TESTING", "1")
