"""Tests for rate resolution helpers."""

from __future__ import annotations

from vectortrack.db.rate_resolver import resolve_rate


def test_resolve_rate_prefers_override():
    assert resolve_rate("P-1", default_rate=75.0, project_hourly_rate=100.0, override_rate=150.0) == 150.0


def test_resolve_rate_uses_project_rate():
    assert resolve_rate("P-1", default_rate=75.0, project_hourly_rate=100.0) == 100.0


def test_resolve_rate_uses_default_for_unassigned():
    assert resolve_rate("", default_rate=75.0, project_hourly_rate=100.0) == 75.0


def test_resolve_rate_falls_back_to_default_for_unknown_project():
    assert resolve_rate("P-1", default_rate=75.0) == 75.0
