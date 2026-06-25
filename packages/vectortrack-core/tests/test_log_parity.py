"""Cross-product log parser parity tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from vectortrack_core.log.parser import parse_sessions

FIXTURE = Path(__file__).parent / "fixtures" / "sample_log.txt"
FIXTURE_NOW = datetime(2025, 6, 2, 12, 0, 0)


@pytest.fixture
def sample_log_content() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_parse_sessions_sample_log(sample_log_content: str) -> None:
    sessions, total_hours = parse_sessions(
        sample_log_content, "TestProject.vwx", now=FIXTURE_NOW
    )
    assert len(sessions) == 3
    assert total_hours == pytest.approx(8.5, rel=1e-3)


def test_desktop_shim_matches_core(sample_log_content: str) -> None:
    try:
        from vectortrack.log_parser import parse_sessions as desktop_parse
    except ImportError:
        pytest.skip("desktop package not installed")
    core_sessions, core_total = parse_sessions(
        sample_log_content, "TestProject.vwx", now=FIXTURE_NOW
    )
    desktop_sessions, desktop_total = desktop_parse(
        sample_log_content, "TestProject.vwx", now=FIXTURE_NOW
    )
    assert len(desktop_sessions) == len(core_sessions)
    assert desktop_total == pytest.approx(core_total, rel=1e-6)


def test_plugin_shim_matches_core(sample_log_content: str) -> None:
    import sys

    plugin_root = Path(__file__).resolve().parents[3] / "VectorTrackScript 0.5"
    if not plugin_root.is_dir():
        pytest.skip("plugin sources not found")
    sys.path.insert(0, str(plugin_root))
    try:
        import vectortrack_log as plugin_log  # noqa: WPS433
    finally:
        if str(plugin_root) in sys.path:
            sys.path.remove(str(plugin_root))

    core_sessions, core_total = parse_sessions(
        sample_log_content, "TestProject.vwx", now=FIXTURE_NOW
    )
    plugin_sessions, plugin_total = plugin_log.parse_sessions(
        sample_log_content, "TestProject.vwx", now=FIXTURE_NOW
    )
    assert len(plugin_sessions) == len(core_sessions)
    assert plugin_total == pytest.approx(core_total, rel=1e-6)
