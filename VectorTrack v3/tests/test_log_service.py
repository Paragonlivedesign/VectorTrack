from datetime import datetime

import pytest

from vectortrack.services.log_service import LogService


def test_log_service_multi_source_dedup(tmp_path):
    log_content = (
        'Opened "MyProject.vwx" at 6/1/2025 9:00:00 AM\n'
        'Closed "MyProject.vwx" at 6/1/2025 10:00:00 AM\n'
    )
    path_a = tmp_path / "a.txt"
    path_b = tmp_path / "b.txt"
    path_a.write_text(log_content, encoding="utf-8")
    path_b.write_text(log_content, encoding="utf-8")

    service = LogService()
    summary = service.get_project_summary("MyProject.vwx", [str(path_a), str(path_b)])
    assert summary.session_count == 1
    assert summary.closed_hours == pytest.approx(1.0, abs=0.01)
    assert summary.trust_score > 0.5


def test_log_service_save_as_alias_mining(tmp_path):
    content = "\n".join(
        [
            'Opened "Project.vwx" at 6/1/2025 9:00:00 AM',
            'Closed "Project.vwx" at 6/1/2025 10:00:00 AM',
            '11/24/2025  7:00:00 PM \tSaved as "Project v2.vwx" from "Project.vwx".',
            'Opened "Project v2.vwx" at 6/1/2025 10:30:00 AM',
            'Closed "Project v2.vwx" at 6/1/2025 11:00:00 AM',
        ]
    )
    log_path = tmp_path / "vw_log.txt"
    log_path.write_text(content, encoding="utf-8")

    service = LogService()
    summary = service.get_project_summary(
        project_name="Project.vwx",
        log_paths=[str(log_path)],
        now=datetime(2025, 6, 1, 12, 0, 0),
    )
    assert summary.closed_hours == pytest.approx(1.5, abs=0.01)
    assert summary.session_count == 2
    assert summary.trust_score >= 0.6


def test_log_service_closed_hours_for_project(tmp_path):
    log_path = tmp_path / "log.txt"
    log_path.write_text(
        '\n'.join(
            [
                'Opened "MyProject.vwx" at 6/2/2025 9:00:00 AM',
                'Closed "MyProject.vwx" at 6/2/2025 11:00:00 AM',
                'Opened "MyProject.vwx" at 6/2/2025 1:00:00 PM',
            ]
        ),
        encoding="utf-8",
    )
    service = LogService()
    hours = service.closed_hours_for_project(
        "MyProject.vwx",
        [str(log_path)],
        now=datetime(2025, 6, 2, 15, 0, 0),
    )
    assert hours == pytest.approx(2.0, abs=0.01)
