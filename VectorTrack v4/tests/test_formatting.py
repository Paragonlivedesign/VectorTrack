"""Tests for display formatting helpers."""

from vectortrack.ui.formatting import project_display_name, resolve_project_code


def test_project_display_name_prefers_name():
    assert project_display_name("Acme Arena", "VT-100") == "Acme Arena"


def test_project_display_name_falls_back_to_code():
    assert project_display_name("", "VT-100") == "VT-100"


def test_resolve_project_code_uses_name_when_code_missing():
    assert resolve_project_code("Acme Arena", "") == "Acme Arena"


def test_resolve_project_code_keeps_explicit_code():
    assert resolve_project_code("Acme Arena", "VT-100") == "VT-100"


def test_resolve_project_code_requires_name():
    assert resolve_project_code("", "VT-100") == ""
