"""Tests for VectorTrackScript v4 (no Vectorworks required)."""

import os
import sys
from datetime import datetime

import pytest

SCRIPT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_ROOT not in sys.path:
    sys.path.insert(0, SCRIPT_ROOT)

from vectortrack_log import (
    build_summary_text,
    find_log_path,
    parse_sessions_for_aliases,
    parse_sessions,
    read_log_content,
)
from vectortrack_rates import DEFAULT_RATE, get_rate, load_rates, set_rate


FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.fixture
def sample_log_content():
    with open(os.path.join(FIXTURES, 'sample_log.txt'), encoding='utf-8') as handle:
        return handle.read()


def test_parse_sessions_closed_and_open(sample_log_content):
    now = datetime(2025, 6, 2, 12, 0, 0)
    sessions, total = parse_sessions(sample_log_content, 'TestProject.vwx', now=now)

    assert len(sessions) == 3
    assert sessions[0].hours == pytest.approx(1.5, abs=0.01)
    assert sessions[1].hours == pytest.approx(3.0, abs=0.01)
    assert sessions[2].is_open is True
    assert sessions[2].hours == pytest.approx(4.0, abs=0.01)
    assert total == pytest.approx(8.5, abs=0.01)


def test_parse_sessions_ignores_other_files(sample_log_content):
    sessions, total = parse_sessions(sample_log_content, 'OtherFile.vwx')
    assert len(sessions) == 1
    assert total == pytest.approx(1.0, abs=0.01)


def test_parse_sessions_no_matches(sample_log_content):
    sessions, total = parse_sessions(sample_log_content, 'Missing.vwx')
    assert sessions == []
    assert total == 0.0


def test_parse_sessions_supports_aliases(sample_log_content):
    sessions, total = parse_sessions(
        sample_log_content,
        'PrimaryProject.vwx',
        aliases=['TestProject.vwx'],
        now=datetime(2025, 6, 2, 12, 0, 0),
    )
    assert len(sessions) == 3
    assert total == pytest.approx(8.5, abs=0.01)


def test_parse_sessions_for_aliases_handles_save_as():
    content = '\n'.join(
        [
            'Opened "Primary.vwx" at 6/1/2025 9:00:00 AM',
            'Saved As "Primary_RevA.vwx" from "Primary.vwx"',
            'Closed "Primary.vwx" at 6/1/2025 10:00:00 AM',
            'Opened "Primary_RevA.vwx" at 6/1/2025 10:15:00 AM',
            'Closed "Primary_RevA.vwx" at 6/1/2025 11:45:00 AM',
        ]
    )
    parsed = parse_sessions_for_aliases(content, ['Primary.vwx'])
    sessions, total = parsed['Primary.vwx']
    assert len(sessions) == 2
    assert total == pytest.approx(2.5, abs=0.01)


def test_build_summary_includes_totals(sample_log_content):
    now = datetime(2025, 6, 2, 12, 0, 0)
    sessions, total = parse_sessions(sample_log_content, 'TestProject.vwx', now=now)
    summary = build_summary_text('TestProject.vwx', sessions, total, 100.0)
    assert 'TestProject.vwx' in summary
    assert 'TOTAL AMOUNT' in summary
    assert '$850.00' in summary


def test_find_log_path_with_temp_tree(tmp_path, monkeypatch):
    vw_root = tmp_path / 'Nemetschek' / 'Vectorworks'
    log_2025 = vw_root / '2025' / 'Vectorworks Log.txt'
    log_2025.parent.mkdir(parents=True)
    log_2025.write_text('test log', encoding='utf-8')

    monkeypatch.setattr(
        'vectortrack_log._roaming_root',
        lambda: str(vw_root),
    )
    assert find_log_path(preferred_year=2026) == str(log_2025)
    assert read_log_content(str(log_2025)) == 'test log'


def test_rates_persistence(tmp_path):
    data_dir = str(tmp_path / 'plugin_data')
    assert get_rate(data_dir, 'ProjectA.vwx') == DEFAULT_RATE
    set_rate(data_dir, 'ProjectA.vwx', 125.5)
    assert get_rate(data_dir, 'ProjectA.vwx') == 125.5
    rates = load_rates(data_dir)
    assert rates['ProjectA.vwx'] == 125.5
