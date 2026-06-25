"""Tests for GitHub release update checks."""

from __future__ import annotations

import pytest

from vectortrack.services import update_service
from vectortrack.services.update_service import (
    ReleaseInfo,
    UpdateCheckResult,
    check_for_updates,
    parse_version,
    release_info_from_payload,
)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("v0.5.4-beta", (0, 5, 4)),
        ("0.5.4", (0, 5, 4)),
        ("VectorTrack 0.6.0 beta", (0, 6, 0)),
        ("not-a-version", None),
    ],
)
def test_parse_version(label, expected):
    assert parse_version(label) == expected


def test_release_info_from_payload_finds_installer():
    payload = {
        "tag_name": "v0.5.5-beta",
        "html_url": "https://github.com/Paragonlivedesign/VectorTrack/releases/tag/v0.5.5-beta",
        "body": "Bug fixes",
        "assets": [
            {
                "name": "VectorTrack-0.5.5-Setup.exe",
                "browser_download_url": "https://example.com/VectorTrack-0.5.5-Setup.exe",
            }
        ],
    }
    release = release_info_from_payload(payload)
    assert release is not None
    assert release.version == (0, 5, 5)
    assert release.download_url == "https://example.com/VectorTrack-0.5.5-Setup.exe"
    assert release.notes == "Bug fixes"


def test_check_for_updates_reports_newer_version(monkeypatch):
    monkeypatch.setattr(update_service, "APP_VERSION", "0.5.4")
    monkeypatch.setattr(
        update_service,
        "fetch_latest_release",
        lambda api_url=update_service.GITHUB_RELEASES_LATEST_API: ReleaseInfo(
            version=(0, 5, 5),
            version_label="0.5.5-beta",
            release_url="https://example.com/release",
            download_url="https://example.com/setup.exe",
            notes="New build",
        ),
    )
    result = check_for_updates()
    assert result.error is None
    assert result.update_available is True
    assert result.latest is not None
    assert result.latest.version == (0, 5, 5)


def test_check_for_updates_reports_current_version(monkeypatch):
    monkeypatch.setattr(update_service, "APP_VERSION", "0.5.4")
    monkeypatch.setattr(
        update_service,
        "fetch_latest_release",
        lambda api_url=update_service.GITHUB_RELEASES_LATEST_API: ReleaseInfo(
            version=(0, 5, 4),
            version_label="0.5.4-beta",
            release_url="https://example.com/release",
            download_url=None,
            notes="",
        ),
    )
    result = check_for_updates()
    assert result.error is None
    assert result.update_available is False


def test_check_for_updates_handles_network_error(monkeypatch):
    def _raise_offline(api_url=update_service.GITHUB_RELEASES_LATEST_API):
        raise RuntimeError("offline")

    monkeypatch.setattr(update_service, "fetch_latest_release", _raise_offline)
    result = check_for_updates()
    assert result.latest is None
    assert result.error == "offline"


def test_update_check_result_update_available_property():
    current = UpdateCheckResult(current_version=(0, 5, 4), latest=None, error="failed")
    assert current.update_available is False

    latest = ReleaseInfo(
        version=(0, 5, 5),
        version_label="0.5.5-beta",
        release_url="https://example.com/release",
        download_url=None,
        notes="",
    )
    available = UpdateCheckResult(current_version=(0, 5, 4), latest=latest)
    assert available.update_available is True

    same = UpdateCheckResult(
        current_version=(0, 5, 4),
        latest=ReleaseInfo(
            version=(0, 5, 4),
            version_label="0.5.4-beta",
            release_url="https://example.com/release",
            download_url=None,
            notes="",
        ),
    )
    assert same.update_available is False
