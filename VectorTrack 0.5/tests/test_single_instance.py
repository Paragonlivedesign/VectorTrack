"""Tests for single-instance guard."""

import os

from vectortrack.single_instance import INSTANCE_KEY, SingleInstanceGuard


def test_acquire_allowed_in_testing_mode(monkeypatch):
    monkeypatch.setenv("VECTORTRACK_TESTING", "1")
    guard = SingleInstanceGuard()
    assert guard.acquire() is True


def test_instance_key_is_stable():
    assert "VectorTrack" in INSTANCE_KEY


def test_notify_existing_is_noop_in_testing_mode(monkeypatch):
    monkeypatch.setenv("VECTORTRACK_TESTING", "1")
    SingleInstanceGuard.notify_existing()
