"""Tests for Vectorworks log parser."""

from datetime import datetime

import pytest

from vectortrack.log_parser import (
    expected_log_path_for_exe,
    expected_log_path_for_year,
    get_balance_delta,
    get_log_reconciliation,
    get_total_log_hours_for_file,
    parse_sessions,
    resolve_log_paths,
    extract_year_from_vw_exe,
)

CLOSED_LOG = """
Opened "MyProject.vwx" at 6/1/2025 9:00:00 AM
Closed "MyProject.vwx" at 6/1/2025 11:00:00 AM
Opened "MyProject.vwx" at 6/2/2025 1:00:00 PM
Closed "MyProject.vwx" at 6/2/2025 3:00:00 PM
"""

OPEN_LOG = """
Opened "MyProject.vwx" at 6/1/2025 9:00:00 AM
Closed "MyProject.vwx" at 6/1/2025 11:00:00 AM
Opened "MyProject.vwx" at 6/2/2025 1:00:00 PM
"""

NATIVE_LOG = """
11/24/2025  6:38:53 PM \tOpened "PLD Start v2.vwx".
11/24/2025  8:05:43 PM \tClosed "PLD Start v2.vwx".
"""


def test_parse_sessions_closed_only():
    sessions, total = parse_sessions(CLOSED_LOG, "MyProject.vwx")
    assert len(sessions) == 2
    assert total == pytest.approx(4.0, abs=0.01)


def test_parse_sessions_open_session():
    now = datetime(2025, 6, 2, 15, 0, 0)
    sessions, total = parse_sessions(OPEN_LOG, "MyProject.vwx", now=now)
    assert len(sessions) == 2
    assert sessions[-1].is_open is True
    assert total == pytest.approx(4.0, abs=0.01)


def test_get_total_log_hours_merges_years(tmp_path, monkeypatch):
    vw_root = tmp_path / "Nemetschek" / "Vectorworks"
    log_2025 = vw_root / "2025" / "Vectorworks Log.txt"
    log_2026 = vw_root / "2026" / "Vectorworks Log.txt"
    log_2025.parent.mkdir(parents=True)
    log_2026.parent.mkdir(parents=True)
    log_2025.write_text(CLOSED_LOG, encoding="utf-8")
    log_2026.write_text(
        'Opened "MyProject.vwx" at 1/1/2026 9:00:00 AM\n'
        'Closed "MyProject.vwx" at 1/1/2026 10:00:00 AM\n',
        encoding="utf-8",
    )

    monkeypatch.setattr("vectortrack_core.log.parser._roaming_root", lambda: str(vw_root))
    total, count, paths = get_total_log_hours_for_file("MyProject.vwx")
    assert total == pytest.approx(5.0, abs=0.01)
    assert count == 3
    assert len(paths) == 2


def test_parse_sessions_matches_project_stem_without_extension():
    sessions, total = parse_sessions(CLOSED_LOG, "MyProject")
    assert len(sessions) == 2
    assert total == pytest.approx(4.0, abs=0.01)


def test_parse_sessions_native_vectorworks_format():
    sessions, total = parse_sessions(NATIVE_LOG, "PLD Start v2.vwx")
    assert len(sessions) == 1
    assert total == pytest.approx(1.45, abs=0.05)


def test_extract_year_from_vw_exe():
    assert extract_year_from_vw_exe(r"C:\Program Files\Vectorworks2026\Vectorworks2026.exe") == 2026
    assert extract_year_from_vw_exe(r"D:\Apps\2025\Vectorworks.exe") == 2025


def test_expected_log_path_for_exe(tmp_path, monkeypatch):
    vw_root = tmp_path / "Nemetschek" / "Vectorworks"
    monkeypatch.setattr("vectortrack_core.log.parser._roaming_root", lambda: str(vw_root))
    assert expected_log_path_for_year(2026) == str(vw_root / "2026" / "Vectorworks Log.txt")
    assert expected_log_path_for_exe(r"C:\Vectorworks2026\Vectorworks2026.exe") == str(
        vw_root / "2026" / "Vectorworks Log.txt"
    )


def test_resolve_log_paths_auto_from_exe(tmp_path, monkeypatch):
    vw_root = tmp_path / "Nemetschek" / "Vectorworks"
    log_2025 = vw_root / "2025" / "Vectorworks Log.txt"
    log_2026 = vw_root / "2026" / "Vectorworks Log.txt"
    log_2025.parent.mkdir(parents=True)
    log_2026.parent.mkdir(parents=True)
    log_2025.write_text(CLOSED_LOG, encoding="utf-8")
    log_2026.write_text("", encoding="utf-8")

    monkeypatch.setattr("vectortrack_core.log.parser._roaming_root", lambda: str(vw_root))
    paths, desc = resolve_log_paths(
        vw_exe_path=r"C:\Vectorworks2026\Vectorworks2026.exe",
        merge_other_years=False,
    )
    assert paths == [str(log_2026)]
    assert "2026" in desc


def test_resolve_log_paths_manual_override(tmp_path, monkeypatch):
    vw_root = tmp_path / "Nemetschek" / "Vectorworks"
    log_2025 = vw_root / "2025" / "Vectorworks Log.txt"
    log_2026 = vw_root / "2026" / "Vectorworks Log.txt"
    log_2025.parent.mkdir(parents=True)
    log_2026.parent.mkdir(parents=True)
    log_2025.write_text(CLOSED_LOG, encoding="utf-8")
    log_2026.write_text("", encoding="utf-8")

    monkeypatch.setattr("vectortrack_core.log.parser._roaming_root", lambda: str(vw_root))
    paths, desc = resolve_log_paths(
        manual_log_path=str(log_2025),
        merge_other_years=False,
    )
    assert paths == [str(log_2025)]
    assert desc.startswith("Manual:")


def test_log_reconciliation_splits_closed_and_open(tmp_path, monkeypatch):
    vw_root = tmp_path / "Nemetschek" / "Vectorworks"
    log_path = vw_root / "2026" / "Vectorworks Log.txt"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(OPEN_LOG, encoding="utf-8")

    monkeypatch.setattr("vectortrack_core.log.parser._roaming_root", lambda: str(vw_root))
    now = datetime(2025, 6, 2, 15, 0, 0)
    recon = get_log_reconciliation("MyProject.vwx", vt_live_hours=1.0, now=now)

    assert recon.closed_hours == pytest.approx(2.0, abs=0.01)
    assert recon.current_open_hours == pytest.approx(2.0, abs=0.01)
    assert get_balance_delta(recon, 1.0) == pytest.approx(1.0, abs=0.01)
